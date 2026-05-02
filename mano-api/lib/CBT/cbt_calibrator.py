"""
Component 4 — CBT distortion-classifier probability calibration.

``lib/activity/cbt_multilabel.select_multi_distortions`` treats the
0.20 per-class threshold as a *calibrated* probability. That contract
only holds if the 11-class softmax out of the sklearn MLP is itself
calibrated. Since sklearn MLPClassifier (like every cross-entropy-
trained deep classifier, Guo et al. 2017) is usually over-confident,
the raw threshold will miss secondary distortions and over-trigger
the "none" gate.

This module loads a frozen temperature / isotonic calibrator from
``ml_models/component4/cbt_calibration.json`` and exposes
``calibrate(probs)`` / ``calibrate_prob_dict(d)``. If the JSON is
absent, the service degrades to identity — the multi-label pipeline
keeps working, just uncalibrated, with a warning.

The module intentionally reuses pure-numpy primitives from
``lib.assesment.calibrator`` (apply_temperature / apply_isotonic /
ECE / Brier) rather than reimplementing them.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from lib.assesment.calibrator import (
    CalibrationMetrics,
    HeadCalibration,
    ReliabilityBin,
    apply_isotonic,
    apply_temperature,
    compute_metrics,
)
from lib.CBT.cbt_multilabel import (
    DISTORTION_CLASS_NAMES,
    NONE_CLASS_NAME,
)

logger = logging.getLogger("component4.cbt_calibrator")

_EPS = 1e-10

# ``DISTORTION_CLASS_NAMES`` already contains "none" at the end; we
# pull it out and pin "none" to index 0 so calibration.json reads
# naturally (none=0, 10 distortions after). The tuple filter handles
# the dedupe explicitly so a reader doesn't have to know "none" is
# inside DISTORTION_CLASS_NAMES.
_NON_NONE_DISTORTIONS: Tuple[str, ...] = tuple(
    name for name in DISTORTION_CLASS_NAMES if name != NONE_CLASS_NAME
)
CLASS_ORDER: Tuple[str, ...] = (NONE_CLASS_NAME,) + _NON_NONE_DISTORTIONS
NUM_CLASSES: int = len(CLASS_ORDER)

DEFAULT_CALIBRATION_PATH = Path(
    os.path.join(
        os.path.dirname(__file__), "..", "..",
        "ml_models", "component4", "cbt_calibration.json",
    )
)


# ─── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CBTCalibration:
    """Frozen parameters for the CBT multi-class calibrator.

    Mirrors the ``HeadCalibration`` shape from Component 2 but keyed
    against the CBT 11-class vector. Kept as its own type because we
    also store ``class_names`` and ``fit_date`` — diagnostics the
    assessment calibrator doesn't need.
    """
    method: str                           # "temperature" | "isotonic" | "identity"
    temperature: float = 1.0
    isotonic_x: Optional[List[List[float]]] = None
    isotonic_y: Optional[List[List[float]]] = None
    n_classes: int = NUM_CLASSES
    class_names: Tuple[str, ...] = CLASS_ORDER
    raw_metrics: Optional[CalibrationMetrics] = None
    calibrated_metrics: Optional[CalibrationMetrics] = None
    fit_date: Optional[str] = None
    n_calibration_samples: int = 0

    def to_dict(self) -> Dict:
        return {
            "method": self.method,
            "temperature": float(self.temperature),
            "isotonic_x": self.isotonic_x,
            "isotonic_y": self.isotonic_y,
            "n_classes": int(self.n_classes),
            "class_names": list(self.class_names),
            "raw_metrics": self.raw_metrics.to_dict() if self.raw_metrics else None,
            "calibrated_metrics": (
                self.calibrated_metrics.to_dict() if self.calibrated_metrics else None
            ),
            "fit_date": self.fit_date,
            "n_calibration_samples": int(self.n_calibration_samples),
        }

    @classmethod
    def identity(cls) -> "CBTCalibration":
        return cls(method="identity", temperature=1.0)

    @classmethod
    def from_dict(cls, d: Mapping) -> "CBTCalibration":
        return cls(
            method=str(d.get("method", "identity")),
            temperature=float(d.get("temperature", 1.0)),
            isotonic_x=d.get("isotonic_x"),
            isotonic_y=d.get("isotonic_y"),
            n_classes=int(d.get("n_classes", NUM_CLASSES)),
            class_names=tuple(d.get("class_names", CLASS_ORDER)),
            raw_metrics=_metrics_from_dict(d.get("raw_metrics")),
            calibrated_metrics=_metrics_from_dict(d.get("calibrated_metrics")),
            fit_date=d.get("fit_date"),
            n_calibration_samples=int(d.get("n_calibration_samples", 0)),
        )


def _metrics_from_dict(d: Optional[Mapping]) -> Optional[CalibrationMetrics]:
    if not d:
        return None
    bins = [
        ReliabilityBin(
            bin_lower=float(b.get("bin_lower", 0.0)),
            bin_upper=float(b.get("bin_upper", 0.0)),
            n_samples=int(b.get("n_samples", 0)),
            mean_confidence=float(b.get("mean_confidence", 0.0)),
            empirical_accuracy=float(b.get("empirical_accuracy", 0.0)),
        )
        for b in (d.get("reliability_bins") or [])
    ]
    return CalibrationMetrics(
        ece=float(d.get("ece", 0.0)),
        brier=float(d.get("brier", 0.0)),
        accuracy=float(d.get("accuracy", 0.0)),
        n_samples=int(d.get("n_samples", 0)),
        reliability_bins=bins,
    )


# ─── Vector helpers ───────────────────────────────────────────────────────────

def prob_dict_to_vector(
    prob_dict: Mapping[str, float],
    *,
    class_order: Sequence[str] = CLASS_ORDER,
) -> np.ndarray:
    """Turn a ``{class_name: prob}`` dict into a fixed-order array.

    Missing classes become 0.0. We do NOT renormalise — the caller has
    already validated the probability simplex upstream
    (``cbt_multilabel._validate_probs``).
    """
    out = np.zeros(len(class_order), dtype=float)
    for i, name in enumerate(class_order):
        out[i] = float(prob_dict.get(name, 0.0))
    return out


def vector_to_prob_dict(
    vec: np.ndarray,
    *,
    class_order: Sequence[str] = CLASS_ORDER,
) -> Dict[str, float]:
    """Inverse of ``prob_dict_to_vector``. Lossless if ``class_order`` matches."""
    return {name: float(vec[i]) for i, name in enumerate(class_order)}


def _reorder_to_canonical(
    probs_matrix: np.ndarray,
    source_order: Sequence[str],
    target_order: Sequence[str] = CLASS_ORDER,
) -> np.ndarray:
    """Permute columns from ``source_order`` to ``target_order``.

    Used when the caller's model orders classes differently — e.g.
    sklearn LabelEncoder sorts alphabetically, putting
    "all_or_nothing" ahead of "none". Missing target classes become
    zero columns (shouldn't happen in production).
    """
    n, _ = probs_matrix.shape
    out = np.zeros((n, len(target_order)), dtype=float)
    src_index = {name: i for i, name in enumerate(source_order)}
    for i, name in enumerate(target_order):
        src = src_index.get(name)
        if src is not None:
            out[:, i] = probs_matrix[:, src]
    return out


# ─── Service ──────────────────────────────────────────────────────────────────

class CbtCalibrationService:
    """Thin adapter around a frozen ``CBTCalibration`` object.

    * Load ``cbt_calibration.json`` once at construction.
    * ``calibrate(probs)`` — accepts 1-D, 2-D arrays, returns same shape.
    * ``calibrate_prob_dict(d)`` — dict-in / dict-out convenience wrapper.
    * ``status()`` — JSON-ready dict for the diagnostics endpoint.

    Kept as an instantiable class (not a module singleton) so tests can
    target a fixture path without polluting import-time state; a
    process-wide singleton is available via ``default_service()``.
    """

    def __init__(
        self,
        calibration: Optional[CBTCalibration] = None,
        *,
        source_path: Optional[Path] = None,
    ):
        self.calibration = calibration or CBTCalibration.identity()
        self.source_path = Path(source_path) if source_path else None

    # ----- loading ------------------------------------------------------------

    @classmethod
    def from_path(cls, path: os.PathLike | str) -> "CbtCalibrationService":
        """Construct from disk. Falls back to identity if absent or corrupt."""
        p = Path(path)
        if not p.exists():
            logger.warning(
                "cbt_calibration.json not found at %s — CBT probabilities "
                "will be passed through uncalibrated. Run "
                "component4-models/step5-cbt-distortion-detector/"
                "fit_cbt_calibration.py to fit parameters.",
                p,
            )
            return cls(CBTCalibration.identity(), source_path=p)
        try:
            with open(p, "r", encoding="utf-8") as f:
                payload = json.load(f)
            body = payload.get("calibration") or payload
            return cls(CBTCalibration.from_dict(body), source_path=p)
        except Exception as exc:  # pragma: no cover — logged and degraded
            logger.error(
                "Failed to load cbt_calibration.json at %s: %s — falling back "
                "to identity.", p, exc,
            )
            return cls(CBTCalibration.identity(), source_path=p)

    # ----- introspection ------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        return self.calibration.method != "identity"

    @property
    def method(self) -> str:
        return self.calibration.method

    def status(self) -> Dict:
        c = self.calibration
        return {
            "loaded": self.source_path is not None and self.source_path.exists(),
            "path": str(self.source_path) if self.source_path else None,
            "is_fitted": self.is_fitted,
            "method": c.method,
            "temperature": round(float(c.temperature), 4),
            "n_classes": int(c.n_classes),
            "class_names": list(c.class_names),
            "n_calibration_samples": int(c.n_calibration_samples),
            "fit_date": c.fit_date,
            "raw_metrics": c.raw_metrics.to_dict() if c.raw_metrics else None,
            "calibrated_metrics": (
                c.calibrated_metrics.to_dict() if c.calibrated_metrics else None
            ),
            "ece_improvement": self._ece_improvement(),
        }

    def _ece_improvement(self) -> Optional[float]:
        c = self.calibration
        if c.raw_metrics is None or c.calibrated_metrics is None:
            return None
        raw = c.raw_metrics.ece
        cal = c.calibrated_metrics.ece
        if raw <= 0:
            return None
        return round(float((raw - cal) / raw), 4)

    # ----- calibrate (array path) ---------------------------------------------

    def calibrate(
        self,
        probs,
        *,
        class_order: Optional[Sequence[str]] = None,
    ) -> np.ndarray:
        """Apply the stored calibrator to a probability array.

        ``probs`` is 1-D ``(C,)`` or 2-D ``(N, C)``. Dicts must go
        through ``calibrate_prob_dict`` instead. If ``class_order`` is
        given and differs from ``CLASS_ORDER``, columns are permuted
        on the way in and out so the caller's order is preserved.
        """
        if isinstance(probs, Mapping):
            raise TypeError(
                "calibrate() does not accept dict; use calibrate_prob_dict()"
            )

        arr = np.asarray(probs, dtype=float)
        one_d = arr.ndim == 1
        if one_d:
            arr = arr.reshape(1, -1)
        if arr.ndim != 2:
            raise ValueError(f"probs must be 1-D or 2-D, got ndim={arr.ndim}")

        source_order = tuple(class_order) if class_order else CLASS_ORDER
        needs_permute = tuple(source_order) != CLASS_ORDER
        work = (
            _reorder_to_canonical(arr, source_order, CLASS_ORDER)
            if needs_permute else arr
        )

        method = self.calibration.method
        if method == "temperature":
            T = float(self.calibration.temperature)
            calibrated = work if abs(T - 1.0) < 1e-9 else apply_temperature(work, T)
        elif method == "isotonic":
            xs = [np.asarray(x, dtype=float) for x in (self.calibration.isotonic_x or [])]
            ys = [np.asarray(y, dtype=float) for y in (self.calibration.isotonic_y or [])]
            if not xs or not ys or len(xs) != work.shape[1]:
                logger.warning(
                    "Isotonic params missing or length-mismatched "
                    "(expected %d, got %d/%d) — passing through.",
                    work.shape[1], len(xs), len(ys),
                )
                calibrated = work
            else:
                calibrated = apply_isotonic(work, xs, ys)
        else:
            calibrated = work

        if needs_permute:
            calibrated = _reorder_to_canonical(
                calibrated, CLASS_ORDER, source_order,
            )

        row_sums = calibrated.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums < _EPS, 1.0, row_sums)
        calibrated = calibrated / row_sums

        return calibrated[0] if one_d else calibrated

    def calibrate_prob_dict(
        self,
        prob_dict: Mapping[str, float],
    ) -> Dict[str, float]:
        """Calibrate a ``{class_name: prob}`` dict, preserving shape.

        Classes not in ``CLASS_ORDER`` are passed through with their
        original value in the output so unexpected keys never silently
        vanish. Known classes are calibrated and renormalised together.
        """
        vec = prob_dict_to_vector(prob_dict, class_order=CLASS_ORDER)
        unknown = {
            k: float(v) for k, v in prob_dict.items() if k not in CLASS_ORDER
        }
        calibrated_vec = self.calibrate(vec)
        out = vector_to_prob_dict(calibrated_vec, class_order=CLASS_ORDER)
        out.update(unknown)
        return out


# ─── Persistence ──────────────────────────────────────────────────────────────

def save_cbt_calibration(
    path: os.PathLike | str,
    calibration: CBTCalibration,
    *,
    fit_metadata: Optional[Dict] = None,
) -> None:
    """Write calibration.json in a forward-compatible envelope."""
    payload = {
        "schema_version": 1,
        "component": "component4.cbt",
        "fit_metadata": fit_metadata or {},
        "calibration": calibration.to_dict(),
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_cbt_calibration(
    path: os.PathLike | str = DEFAULT_CALIBRATION_PATH,
) -> CBTCalibration:
    """Load the ``CBTCalibration`` payload. Returns identity if absent."""
    p = Path(path)
    if not p.exists():
        return CBTCalibration.identity()
    with open(p, "r", encoding="utf-8") as f:
        payload = json.load(f)
    body = payload.get("calibration") or payload
    return CBTCalibration.from_dict(body)


# ─── Singleton ────────────────────────────────────────────────────────────────

_default_service: Optional[CbtCalibrationService] = None


def default_service(
    *,
    path: os.PathLike | str = DEFAULT_CALIBRATION_PATH,
    reload: bool = False,
) -> CbtCalibrationService:
    """Lazy process-wide singleton. Tests pass ``reload=True`` for a fresh load."""
    global _default_service
    if _default_service is None or reload:
        _default_service = CbtCalibrationService.from_path(path)
    return _default_service


def reset_default_service() -> None:
    """Clear the cached singleton. Tests only."""
    global _default_service
    _default_service = None
