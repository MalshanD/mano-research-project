"""
Canonical patient-state <-> tensor helpers.

Previously each router module hand-rolled its own ``parse_patient_state`` and
``clamp_simulated_vitals``. That drift is a maintenance trap: if feature order
or clamp ranges ever change (they shouldn't — the models are frozen), a
subtle divergence between routers would silently corrupt inferences.

This module is the SINGLE source of truth for:

* converting a ``PatientState`` Pydantic payload into the dynamic + static
  numpy arrays expected by the frozen Seq2Seq / Hybrid-LSTM / PPO models, and
* clamping raw Seq2Seq outputs back into schema-valid ``DayVitals``.

Feature ordering mirrors the exact order used during model training — any
deviation from this order WILL silently corrupt predictions while still
producing "valid" responses, which is the worst class of bug.

──────────────────────────────────────────────────────────────────────────────
NORMALISATION (BUG FIX — Inverse Risk Calculation)
──────────────────────────────────────────────────────────────────────────────
Both the Seq2Seq Simulator and the Hybrid-LSTM were trained on MinMax-
normalised vitals in [0, 1].  Raw user input (e.g. sleep_hours=9.0,
heart_rate=72) is NOT in that range, so feeding it un-normalised saturates
the model weights and produces nonsensical — often inverted — predictions.

Root cause:  parse_patient_state was returning raw units; the Seq2Seq Decoder
             applies a final Sigmoid (output in [0,1]) and the LSTM was never
             exposed to values like 9.0 or 72.0 during training.

Fix:  ``parse_patient_state`` now normalises the dynamic feature matrix into
      [0, 1] before returning it.  ``_denormalize_dynamic`` is the inverse
      transform used by ``clamp_simulated_vitals`` to restore model outputs to
      human-readable units for the frontend charts.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from schemas.synthetic.simulation_schema import DayVitals, PatientState


# ── Feature-order canonicals ───────────────────────────────────────────────
#
# Documented here so downstream reviewers can audit without reading model
# checkpoints. Changing these without retraining the frozen models is a
# correctness bug — they are effectively immutable.
DYNAMIC_FEATURE_ORDER: Tuple[str, ...] = (
    "sleep_hours",
    "sleep_quality",
    "heart_rate",
    "stress_level",
)

# Clamp ranges for raw (denormalised) vitals — used after inverse-transform.
_CLAMP_RANGES = {
    "sleep_hours": (0.0, 24.0),
    "sleep_quality": (0.0, 1.0),
    "heart_rate": (40.0, 200.0),
    "stress_level": (0.0, 1.0),
}

# ── MinMax normalisation constants ────────────────────────────────────────
#
# These MUST match the scaler fitted on the training dataset.
# Feature order: [sleep_hours, sleep_quality, heart_rate, stress_level]
#
#   sleep_hours  : raw [0, 12]   → normalised [0, 1]
#   sleep_quality: raw [0, 1]    → already [0, 1]  (no-op: min=0, max=1)
#   heart_rate   : raw [50, 120] → normalised [0, 1]
#   stress_level : raw [0, 1]    → already [0, 1]  (no-op: min=0, max=1)
_FEATURE_MIN = np.array([0.0,  0.0,  50.0, 0.0], dtype=np.float32)
_FEATURE_MAX = np.array([12.0, 1.0, 120.0, 1.0], dtype=np.float32)
_FEATURE_RANGE = _FEATURE_MAX - _FEATURE_MIN  # [12.0, 1.0, 70.0, 1.0]


def _normalize_dynamic(raw: np.ndarray) -> np.ndarray:
    """MinMax-normalise a (1, T, 4) dynamic array into [0, 1].

    Clamps the raw values to the training min/max before dividing so that
    extreme out-of-range inputs don't produce negative or >1 normalised values.
    """
    clipped = np.clip(raw, _FEATURE_MIN, _FEATURE_MAX)
    return (clipped - _FEATURE_MIN) / _FEATURE_RANGE


def _denormalize_dynamic(normalised: np.ndarray) -> np.ndarray:
    """Inverse of ``_normalize_dynamic``: maps [0, 1] back to raw units.

    Used to convert Seq2Seq outputs (which are in normalised space due to the
    Sigmoid activation in the Decoder) back to human-readable values.
    """
    return normalised * _FEATURE_RANGE + _FEATURE_MIN


def parse_patient_state(state: PatientState) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a validated ``PatientState`` payload into inference tensors.

    Returns a ``(dynamic_np, static_np)`` tuple with shapes::

        dynamic_np: (1, T, 4)   — T days × 4 features, MinMax-normalised to [0, 1]
        static_np:  (1, 20)     — demographic / historical feature vector

    The leading ``1`` is the batch dimension; we always infer one patient at a
    time at the route layer (batch APIs sit on top of this).

    IMPORTANT — normalisation:
        The Seq2Seq and Hybrid-LSTM checkpoints were trained on MinMax-scaled
        vitals.  Raw values (e.g. sleep_hours=9, heart_rate=72) MUST be
        normalised before inference or the models receive out-of-distribution
        inputs and produce inverted / nonsensical predictions.  This function
        applies that normalisation automatically — callers must NOT normalise
        again.
    """
    static_np = np.array([state.static_data.features], dtype=np.float32)

    dyn_rows: List[List[float]] = []
    for day in state.dynamic_history:
        dyn_rows.append([
            float(day.sleep_hours),
            float(day.sleep_quality),
            float(day.heart_rate),
            float(day.stress_level),
        ])

    # Shape: (1, T, 4) — raw units from the Pydantic model
    dynamic_raw = np.array([dyn_rows], dtype=np.float32)

    # ── Normalise to [0, 1] to match the training distribution ──
    dynamic_np = _normalize_dynamic(dynamic_raw)

    return dynamic_np, static_np


def clamp_simulated_vitals(future_dyn_np: np.ndarray) -> List[DayVitals]:
    """Project Seq2Seq output (normalised [0, 1]) into schema-valid ``DayVitals``.

    The Seq2Seq Decoder applies a final Sigmoid so its raw outputs are in
    [0, 1] (normalised space).  We first denormalise back to real-world units
    (e.g. sleep_hours → [0, 12], heart_rate → [50, 120]) then clamp to the
    schema limits to guard against tiny floating-point overshoots.
    """
    # Step 1: Denormalise — [0, 1] → raw units
    future_raw = _denormalize_dynamic(future_dyn_np)

    # Step 2: Clamp to schema-valid ranges and wrap in DayVitals
    vitals: List[DayVitals] = []
    for day_idx in range(future_raw.shape[1]):
        row = future_raw[0, day_idx]
        vitals.append(DayVitals(
            sleep_hours=float(np.clip(row[0], *_CLAMP_RANGES["sleep_hours"])),
            sleep_quality=float(np.clip(row[1], *_CLAMP_RANGES["sleep_quality"])),
            heart_rate=float(np.clip(row[2], *_CLAMP_RANGES["heart_rate"])),
            stress_level=float(np.clip(row[3], *_CLAMP_RANGES["stress_level"])),
        ))
    return vitals


def vitals_to_matrix(vitals: List[DayVitals]) -> np.ndarray:
    """Inverse of ``clamp_simulated_vitals`` — list of DayVitals → (1, T, 4).

    Returns raw-unit values (not normalised).  If you need a normalised tensor
    for model input, call ``_normalize_dynamic`` on the result.
    """
    rows = [[v.sleep_hours, v.sleep_quality, v.heart_rate, v.stress_level] for v in vitals]
    return np.array([rows], dtype=np.float32)
