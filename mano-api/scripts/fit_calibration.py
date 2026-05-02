"""
Offline calibration fitter for Component 2 (risk prediction).

Run this ONCE after model training or any model checkpoint swap, on a
machine that has tensorflow + sklearn installed. It:

  1. Loads the frozen Keras Dense NN, scaler, and label encoders from
     ``ml_models/component2/``.
  2. Pulls a labelled calibration cohort (see ``--cohort``).
  3. Runs the model to collect raw softmax per head (stress / anxiety /
     depression).
  4. Fits two calibrators per head — temperature scaling and
     per-class isotonic regression — then picks the one with lower ECE.
  5. Writes ``ml_models/component2/calibration.json`` with the frozen
     parameters + raw vs calibrated metrics + fit metadata.

After that, ``lib/assesment/predictor.py`` will pick up the file on the
next process start and route every prediction through it — no code
changes, no redeploy of the model itself.

Usage
-----

    python scripts/fit_calibration.py --cohort path/to/labelled.csv
    python scripts/fit_calibration.py --synthetic  # demo-only fallback

The CSV must contain the 16 FEATURE_COLUMNS plus three integer label
columns: ``stress_label``, ``anxiety_label``, ``depression_label`` with
values in {0,1,2} = {low, moderate, high}.

Why not auto-fit on first request?
----------------------------------
Fitting is a cohort-level operation — doing it per-request would be
both slow and *wrong* (you'd be calibrating on a moving window of one
patient's predictions). This keeps the online service deterministic and
isolates calibration decisions to a reviewable artefact on disk.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

# Make lib.* importable when running as a script.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fit_calibration")


def _load_frozen_model():
    """Import tf + load model lazily so the script can be read without TF."""
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import joblib
    import tensorflow as tf

    tf.config.set_visible_devices([], "GPU")

    model_path = ROOT / "ml_models" / "component2" / "model.keras"
    scaler_path = ROOT / "ml_models" / "component2" / "3-class-scaler.pkl"
    encoders_path = ROOT / "ml_models" / "component2" / "3-class-encoders.pkl"

    for p in (model_path, scaler_path, encoders_path):
        if not p.exists():
            raise FileNotFoundError(f"Required artefact missing: {p}")

    model = tf.keras.models.load_model(model_path)
    scaler = joblib.load(scaler_path)
    encoders = joblib.load(encoders_path)
    return model, scaler, encoders


FEATURE_COLUMNS = [
    "Age", "Gender", "Education_Level", "Employment_Status",
    "Sleep_Hours", "Physical_Activity_Hrs", "Social_Support_Score",
    "Family_History_Mental_Illness", "Chronic_Illnesses",
    "Therapy", "Meditation", "Financial_Stress", "Work_Stress",
    "Self_Esteem_Score", "Life_Satisfaction_Score", "Loneliness_Score",
]
LABEL_COLUMNS = {
    "stress": "stress_label",
    "anxiety": "anxiety_label",
    "depression": "depression_label",
}


def _encode_cohort(df, encoders) -> "np.ndarray":
    import pandas as pd  # local import

    df = df.copy()
    for col, le in encoders.items():
        if col not in df.columns:
            continue
        df[col] = df[col].astype(str)
        unknown = ~df[col].isin(le.classes_)
        if unknown.any():
            raise ValueError(
                f"Unknown values in column {col!r}: "
                f"{df.loc[unknown, col].unique().tolist()}. "
                f"Valid options: {list(le.classes_)}"
            )
        df[col] = le.transform(df[col])
    return df[FEATURE_COLUMNS].to_numpy()


def _load_cohort_csv(path: Path):
    import pandas as pd

    df = pd.read_csv(path)
    missing = [c for c in FEATURE_COLUMNS + list(LABEL_COLUMNS.values()) if c not in df.columns]
    if missing:
        raise ValueError(
            f"Cohort CSV {path} missing required columns: {missing}. "
            f"Need 16 features + stress_label/anxiety_label/depression_label."
        )
    return df


def _synthetic_cohort(n: int, encoders) -> Tuple["np.ndarray", Dict[str, "np.ndarray"]]:
    """Emergency fallback cohort. NOT for production calibration.

    Uses a clinically plausible joint distribution over the 16 features
    and deterministic weak-label rules for stress/anxiety/depression so
    the script can produce a demo calibration.json without labelled
    data. The resulting calibration is only as useful as the weak labels
    — treat it as a sanity-check scaffold, not a real clinical calibration.
    """
    import pandas as pd
    rng = np.random.default_rng(0)

    def _choice_in(le_col, fallback):
        le = encoders.get(le_col)
        if le is None or not hasattr(le, "classes_"):
            return fallback
        return list(le.classes_)

    df = pd.DataFrame({
        "Age": rng.integers(18, 65, size=n),
        "Gender": rng.choice(_choice_in("Gender", ["Male", "Female"]), size=n),
        "Education_Level": rng.choice(
            _choice_in("Education_Level", ["High School", "Bachelor", "Master"]), size=n,
        ),
        "Employment_Status": rng.choice(
            _choice_in("Employment_Status", ["Employed", "Unemployed", "Student"]), size=n,
        ),
        "Sleep_Hours": rng.uniform(4.0, 9.0, size=n).round(1),
        "Physical_Activity_Hrs": rng.uniform(0.0, 5.0, size=n).round(1),
        "Social_Support_Score": rng.integers(1, 11, size=n),
        "Family_History_Mental_Illness": rng.choice(
            _choice_in("Family_History_Mental_Illness", ["Yes", "No"]), size=n,
        ),
        "Chronic_Illnesses": rng.choice(
            _choice_in("Chronic_Illnesses", ["Yes", "No"]), size=n,
        ),
        "Therapy": rng.choice(_choice_in("Therapy", ["Yes", "No"]), size=n),
        "Meditation": rng.choice(_choice_in("Meditation", ["Yes", "No"]), size=n),
        "Financial_Stress": rng.integers(1, 11, size=n),
        "Work_Stress": rng.integers(1, 11, size=n),
        "Self_Esteem_Score": rng.integers(1, 11, size=n),
        "Life_Satisfaction_Score": rng.integers(1, 11, size=n),
        "Loneliness_Score": rng.integers(1, 11, size=n),
    })

    def _bucketise(score: "np.ndarray") -> "np.ndarray":
        out = np.zeros_like(score, dtype=int)
        out[score >= 35] = 1
        out[score >= 70] = 2
        return out

    stress_score = (
        8.0 * df["Work_Stress"] + 5.0 * df["Financial_Stress"]
        + 3.0 * (10 - df["Self_Esteem_Score"])
        + 2.0 * (10 - df["Life_Satisfaction_Score"])
        - 3.0 * df["Sleep_Hours"] - 2.0 * df["Physical_Activity_Hrs"]
    )
    anxiety_score = (
        6.0 * df["Loneliness_Score"] + 4.0 * df["Work_Stress"]
        + 4.0 * (10 - df["Social_Support_Score"])
        + 3.0 * df["Financial_Stress"]
        - 2.5 * df["Sleep_Hours"] - 3.0 * df["Physical_Activity_Hrs"]
    )
    depression_score = (
        7.0 * df["Loneliness_Score"] + 5.0 * (10 - df["Life_Satisfaction_Score"])
        + 4.0 * (10 - df["Self_Esteem_Score"])
        + 3.0 * df["Financial_Stress"]
        - 3.5 * df["Sleep_Hours"] - 2.5 * df["Physical_Activity_Hrs"]
    )
    # Normalise to 0-100 and bucketise with the same thresholds as the
    # predictor's _get_label.
    for s in (stress_score, anxiety_score, depression_score):
        lo, hi = s.min(), s.max()
        if hi - lo > 0:
            s -= lo
            s *= (100.0 / (hi - lo))
    labels = {
        "stress": _bucketise(stress_score.to_numpy()),
        "anxiety": _bucketise(anxiety_score.to_numpy()),
        "depression": _bucketise(depression_score.to_numpy()),
    }
    return df, labels


def _collect_raw_probs(model, features_scaled: "np.ndarray"):
    preds = model.predict(features_scaled, verbose=0)
    # Keras returns a list of 3 arrays, each shape (N, 3) — one per head.
    return {"stress": preds[0], "anxiety": preds[1], "depression": preds[2]}


def _pick_better_method(
    head: str,
    raw_probs: "np.ndarray",
    labels: "np.ndarray",
) -> "HeadCalibration":
    from lib.assesment.calibrator import (
        HeadCalibration,
        apply_isotonic,
        apply_temperature,
        compute_metrics,
        fit_isotonic_per_class,
        fit_temperature,
    )

    raw_metrics = compute_metrics(raw_probs, labels)

    # Fit both and pick the lower-ECE option.
    T, _ = fit_temperature(raw_probs, labels)
    temp_probs = apply_temperature(raw_probs, T)
    temp_metrics = compute_metrics(temp_probs, labels)

    iso_x, iso_y = fit_isotonic_per_class(raw_probs, labels)
    iso_probs = apply_isotonic(raw_probs, iso_x, iso_y)
    iso_metrics = compute_metrics(iso_probs, labels)

    log.info(
        "%-10s raw: ECE=%.4f brier=%.4f  | temp(T=%.3f): ECE=%.4f  | iso: ECE=%.4f",
        head, raw_metrics.ece, raw_metrics.brier, T, temp_metrics.ece, iso_metrics.ece,
    )

    # Prefer temperature if it's within 0.005 ECE of isotonic — it's
    # simpler, preserves argmax, and is less likely to overfit. Otherwise
    # pick the lower-ECE method.
    if temp_metrics.ece <= iso_metrics.ece + 5e-3:
        return HeadCalibration(
            head=head, method="temperature", temperature=float(T),
            raw_metrics=raw_metrics, calibrated_metrics=temp_metrics,
        )
    return HeadCalibration(
        head=head, method="isotonic",
        isotonic_x=[list(map(float, x)) for x in iso_x],
        isotonic_y=[list(map(float, y)) for y in iso_y],
        raw_metrics=raw_metrics, calibrated_metrics=iso_metrics,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--cohort", type=Path, help="Path to labelled CSV cohort")
    src.add_argument("--synthetic", action="store_true",
                     help="Use synthetic cohort (demo only, NOT production).")
    parser.add_argument("--n-synthetic", type=int, default=2000,
                        help="Cohort size when using --synthetic")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "ml_models" / "component2" / "calibration.json",
                        help="Where to write calibration.json")
    args = parser.parse_args()

    log.info("Loading frozen model + scaler + encoders…")
    model, scaler, encoders = _load_frozen_model()

    if args.synthetic:
        log.warning(
            "Running with SYNTHETIC cohort — output is a sanity-check "
            "calibration only. Replace with labelled data for production."
        )
        features_df, labels = _synthetic_cohort(args.n_synthetic, encoders)
        source = f"synthetic(n={args.n_synthetic})"
    else:
        log.info("Loading labelled cohort from %s", args.cohort)
        df = _load_cohort_csv(args.cohort)
        features_df = df[FEATURE_COLUMNS + list(LABEL_COLUMNS.values())]
        labels = {
            head: df[col].to_numpy().astype(int)
            for head, col in LABEL_COLUMNS.items()
        }
        source = str(args.cohort)

    log.info("Encoding + scaling %d samples…", len(features_df))
    encoded = _encode_cohort(features_df[FEATURE_COLUMNS], encoders)
    scaled = scaler.transform(encoded)

    log.info("Running frozen model to collect raw softmax per head…")
    raw = _collect_raw_probs(model, scaled)

    heads = {}
    for head_name in ("stress", "anxiety", "depression"):
        heads[head_name] = _pick_better_method(head_name, raw[head_name], labels[head_name])

    # Write calibration.json.
    from lib.assesment.calibrator import save_calibration
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_calibration(
        args.out, heads,
        fit_metadata={
            "fitted_at": _dt.datetime.utcnow().isoformat() + "Z",
            "cohort_source": source,
            "cohort_size": int(len(features_df)),
            "model_path": "ml_models/component2/model.keras",
        },
    )
    log.info("Wrote calibration to %s", args.out)
    log.info("Selected methods: %s",
             {h: heads[h].method for h in ("stress", "anxiety", "depression")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
