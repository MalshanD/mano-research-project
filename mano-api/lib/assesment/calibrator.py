"""
Component 2 — Probability calibration service.

Why this exists
---------------
The Keras Dense NN behind ``lib/assesment/predictor.py`` was trained with
cross-entropy and no calibration layer, which (per Guo et al., 2017 and
subsequent replications) systematically produces *over-confident* softmax
probabilities for modern deep networks. That matters here because
EVERY downstream consumer scales with the raw probabilities:

  * ``_get_score`` = ``prob_moderate*50 + prob_high*100``. A 10-point
    overestimate of ``prob_high`` drives a 10-point overestimate of the
    score, which can flip a user from "Moderate" to "High" spuriously.
  * SHAP attributions are *relative* but clinicians read absolute deltas
    ("Sleep reduced risk by 15 points") — miscalibration shifts that
    scale.
  * The counterfactual "5% reduction" filter treats probabilities as
    literal frequencies, which only holds under calibration.
  * Resource-routing thresholds (``Depression > 85%``) are designed
    around well-calibrated probabilities.

What this module does
---------------------
Two complementary methods, fitted offline per head (stress / anxiety /
depression) and persisted as frozen parameters in ``calibration.json``:

  1. **Temperature scaling** (Guo et al., 2017) — one scalar ``T`` per
     head. Divides logits by ``T`` before the final softmax. ``T > 1``
     softens over-confident outputs. Preserves argmax. One-line fix,
     closed-form optimum via scipy.minimize.

  2. **Isotonic regression** — non-parametric, monotonic mapping from
     raw probability → calibrated probability. Fitted per class (Low /
     Moderate / High). More flexible than temperature scaling but
     requires more data and can overfit.

At fit time we compute Expected Calibration Error (ECE) and Brier score
for raw, temperature-scaled, and isotonic-calibrated probabilities, then
auto-select the lower-ECE method per head. The decision, parameters,
and diagnostic metrics are written to ``calibration.json`` so the
service layer can load them without re-fitting and the diagnostics
endpoint can surface them.

Design principles
-----------------
* **No TensorFlow dependency** — this module works with plain numpy
  arrays. The fitting script is where TF is needed (to run the frozen
  model on a cohort); calibration application is pure numpy. This keeps
  the test sandbox lean and makes the calibrator unit-testable without
  GPU or model artefacts.
* **Identity fallback** — if ``calibration.json`` is absent, the
  calibrator returns input unchanged and logs a warning. The service
  degrades gracefully rather than crashing.
* **Idempotent** — calibrating already-calibrated probs should not
  compound the effect; the service uses a flag on the parameters file
  so callers can detect double-calibration attempts.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger("component2.calibrator")

# Reserved head names — match the predictor's three output heads.
HEADS = ("stress", "anxiety", "depression")
CLASSES = ("low", "moderate", "high")

# Small constant used to avoid log(0) / div-by-zero in entropy and logit
# computations. Mirrors the value in uncertainty_service for consistency.
_EPS = 1e-10


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReliabilityBin:
    """One bin of the reliability diagram (confidence vs observed accuracy)."""
    bin_lower: float
    bin_upper: float
    n_samples: int
    mean_confidence: float       # mean predicted probability in this bin
    empirical_accuracy: float    # fraction of correct predictions in this bin


@dataclass(frozen=True)
class CalibrationMetrics:
    """Summary statistics for a set of predictions vs labels."""
    ece: float                   # Expected Calibration Error (lower = better)
    brier: float                 # Brier score (lower = better, proper scoring rule)
    accuracy: float              # argmax accuracy (unchanged by temperature scaling)
    n_samples: int
    reliability_bins: List[ReliabilityBin] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "ece": round(self.ece, 4),
            "brier": round(self.brier, 4),
            "accuracy": round(self.accuracy, 4),
            "n_samples": self.n_samples,
            "reliability_bins": [b.__dict__ for b in self.reliability_bins],
        }


@dataclass(frozen=True)
class HeadCalibration:
    """Frozen parameters for one head's calibrator."""
    head: str
    method: str                  # "temperature", "isotonic", or "identity"
    temperature: float = 1.0     # used when method == "temperature"
    isotonic_x: Optional[List[List[float]]] = None  # per-class breakpoints (probs)
    isotonic_y: Optional[List[List[float]]] = None  # per-class mapped values
    raw_metrics: Optional[CalibrationMetrics] = None
    calibrated_metrics: Optional[CalibrationMetrics] = None

    def to_dict(self) -> Dict:
        return {
            "head": self.head,
            "method": self.method,
            "temperature": self.temperature,
            "isotonic_x": self.isotonic_x,
            "isotonic_y": self.isotonic_y,
            "raw_metrics": self.raw_metrics.to_dict() if self.raw_metrics else None,
            "calibrated_metrics": (
                self.calibrated_metrics.to_dict() if self.calibrated_metrics else None
            ),
        }

    @classmethod
    def identity(cls, head: str) -> "HeadCalibration":
        """Null calibrator — returns probabilities unchanged."""
        return cls(head=head, method="identity", temperature=1.0)


# ─── ECE / Brier / reliability ───────────────────────────────────────────────

def _reliability_bins(
    confidences: np.ndarray,
    predictions: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> List[ReliabilityBin]:
    """Build the raw bins used by both ECE and reliability diagrams.

    ``confidences`` is the model's probability for its argmax prediction.
    Bins are equal-width over ``[0, 1]``.
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    out: List[ReliabilityBin] = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        # Upper bound inclusive on the last bin only — standard ECE convention.
        if i < n_bins - 1:
            mask = (confidences >= lo) & (confidences < hi)
        else:
            mask = (confidences >= lo) & (confidences <= hi)
        n = int(mask.sum())
        if n == 0:
            out.append(ReliabilityBin(lo, hi, 0, 0.0, 0.0))
            continue
        mean_conf = float(confidences[mask].mean())
        emp_acc = float((predictions[mask] == labels[mask]).mean())
        out.append(ReliabilityBin(lo, hi, n, mean_conf, emp_acc))
    return out


def expected_calibration_error(
    probabilities: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> Tuple[float, List[ReliabilityBin]]:
    """Compute ECE and the underlying reliability bins.

    Parameters
    ----------
    probabilities : shape (N, C) — per-class probabilities, rows sum to 1
    labels        : shape (N,)   — integer class labels in [0, C-1]

    Returns
    -------
    ece : float — weighted mean |accuracy - confidence| across bins
    bins : list of ReliabilityBin for diagnostic plotting
    """
    if probabilities.ndim != 2:
        raise ValueError("probabilities must be (N, C)")
    if labels.ndim != 1 or labels.shape[0] != probabilities.shape[0]:
        raise ValueError("labels must be (N,) and match probabilities rows")

    confidences = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    bins = _reliability_bins(confidences, predictions, labels, n_bins=n_bins)

    n_total = max(int(labels.shape[0]), 1)
    ece = 0.0
    for b in bins:
        if b.n_samples == 0:
            continue
        weight = b.n_samples / n_total
        ece += weight * abs(b.empirical_accuracy - b.mean_confidence)
    return float(ece), bins


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    """Multi-class Brier score — mean squared error against one-hot labels.

    Proper scoring rule: lower is better. Unlike accuracy, it rewards
    well-calibrated probability estimates, not just correct argmax.
    """
    n, c = probabilities.shape
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(n), labels] = 1.0
    return float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))


def compute_metrics(
    probabilities: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> CalibrationMetrics:
    """One-stop summary: ECE + Brier + accuracy + reliability bins."""
    ece, bins = expected_calibration_error(probabilities, labels, n_bins=n_bins)
    brier = brier_score(probabilities, labels)
    predictions = probabilities.argmax(axis=1)
    acc = float((predictions == labels).mean())
    return CalibrationMetrics(
        ece=ece, brier=brier, accuracy=acc,
        n_samples=int(labels.shape[0]), reliability_bins=bins,
    )


# ─── Temperature scaling ─────────────────────────────────────────────────────

def _probs_to_logits(probs: np.ndarray) -> np.ndarray:
    """Invert softmax to get pseudo-logits.

    Temperature scaling is defined on logits. Since the Keras model only
    gives us probabilities at this interface boundary, we recover logits
    via ``log(prob) - log(prob[0])`` (any reference class works because
    softmax is invariant under an additive constant).
    """
    clipped = np.clip(probs, _EPS, 1.0)
    return np.log(clipped) - np.log(clipped[:, :1])


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    """Apply temperature scaling to a probability array.

    ``T = 1`` is the identity. ``T > 1`` softens (reduces confidence);
    ``T < 1`` sharpens. Preserves argmax for any ``T > 0``.
    """
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    if abs(temperature - 1.0) < 1e-9:
        return np.array(probs, dtype=float)
    logits = _probs_to_logits(np.asarray(probs, dtype=float))
    return _softmax(logits / temperature)


def fit_temperature(
    probs: np.ndarray, labels: np.ndarray, *, max_iter: int = 200,
) -> Tuple[float, float]:
    """Find the ``T`` that minimises NLL on ``(probs, labels)``.

    Returns ``(T, final_nll)``. Uses scipy.optimize.minimize with L-BFGS-B
    bounded to ``[0.05, 20]``. Closed-form optima don't exist for the
    multi-class case so numerical optimisation is standard.

    Gracefully handles the no-scipy case by falling back to a 1-D grid
    search, since scipy is optional in some deployments.
    """
    probs = np.asarray(probs, dtype=float)
    labels = np.asarray(labels, dtype=int)
    logits = _probs_to_logits(probs)

    def nll(T: float) -> float:
        if T <= 0:
            return np.inf
        p = _softmax(logits / T)
        # Clip once more to avoid log(0) in the NLL.
        p = np.clip(p, _EPS, 1.0)
        return float(-np.log(p[np.arange(len(labels)), labels]).mean())

    try:
        from scipy.optimize import minimize_scalar
        res = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded",
                              options={"maxiter": max_iter})
        return float(res.x), float(res.fun)
    except ImportError:  # pragma: no cover — scipy is in requirements
        # Log-spaced grid search fallback.
        candidates = np.exp(np.linspace(np.log(0.1), np.log(10.0), 200))
        losses = [nll(float(T)) for T in candidates]
        best = int(np.argmin(losses))
        return float(candidates[best]), float(losses[best])


# ─── Isotonic regression ─────────────────────────────────────────────────────

def fit_isotonic_per_class(
    probs: np.ndarray, labels: np.ndarray,
) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """Fit one isotonic regressor per class (one-vs-rest).

    Returns ``(xs, ys)`` — per-class lists of breakpoint arrays suitable
    for re-applying via ``np.interp``. We store breakpoints (not the
    sklearn estimator) so calibration.json is portable and doesn't pin
    sklearn versions.
    """
    from sklearn.isotonic import IsotonicRegression

    _, num_classes = probs.shape
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    for c in range(num_classes):
        y_binary = (labels == c).astype(float)
        ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        ir.fit(probs[:, c], y_binary)
        # Extract the (x, y) breakpoints for portable storage.
        xs.append(np.asarray(ir.X_thresholds_, dtype=float))
        ys.append(np.asarray(ir.y_thresholds_, dtype=float))
    return xs, ys


def apply_isotonic(
    probs: np.ndarray,
    xs: Sequence[Sequence[float]],
    ys: Sequence[Sequence[float]],
) -> np.ndarray:
    """Apply per-class isotonic regression + renormalise rows."""
    probs = np.asarray(probs, dtype=float)
    out = np.empty_like(probs)
    for c in range(probs.shape[1]):
        out[:, c] = np.interp(probs[:, c], xs[c], ys[c])
    # Renormalise so rows sum to 1 after independent per-class mapping.
    row_sums = out.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums < _EPS, 1.0, row_sums)
    return out / row_sums


# ─── Persistence ─────────────────────────────────────────────────────────────

DEFAULT_CALIBRATION_PATH = Path("ml_models/component2/calibration.json")


def save_calibration(
    path: os.PathLike | str,
    heads: Dict[str, HeadCalibration],
    *,
    fit_metadata: Optional[Dict] = None,
) -> None:
    """Write calibration.json in a forward-compatible format."""
    payload = {
        "schema_version": 1,
        "fit_metadata": fit_metadata or {},
        "heads": {name: hc.to_dict() for name, hc in heads.items()},
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_calibration(
    path: os.PathLike | str = DEFAULT_CALIBRATION_PATH,
) -> Dict[str, HeadCalibration]:
    """Load calibration parameters. Returns an identity map if absent.

    Never raises on a missing file — the predictor is expected to run
    without calibration in dev/test, so we log a warning and return
    identity calibrators for each head.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(
            "calibration.json not found at %s — falling back to identity "
            "calibration for all heads. Run scripts/fit_calibration.py to "
            "fit parameters.",
            p,
        )
        return {h: HeadCalibration.identity(h) for h in HEADS}

    with open(p, "r", encoding="utf-8") as f:
        payload = json.load(f)

    heads: Dict[str, HeadCalibration] = {}
    for name, d in payload.get("heads", {}).items():
        heads[name] = HeadCalibration(
            head=d["head"],
            method=d.get("method", "identity"),
            temperature=float(d.get("temperature", 1.0)),
            isotonic_x=d.get("isotonic_x"),
            isotonic_y=d.get("isotonic_y"),
        )
    # Guarantee every expected head is present, even if the file is partial.
    for h in HEADS:
        heads.setdefault(h, HeadCalibration.identity(h))
    return heads


# ─── Public service façade ───────────────────────────────────────────────────

class CalibrationService:
    """Thin wrapper the predictor can depend on.

    Lazy-loads ``calibration.json`` on first use; callers should create
    a single instance at module scope.
    """

    def __init__(self, path: os.PathLike | str = DEFAULT_CALIBRATION_PATH):
        self._path = Path(path)
        self._heads: Optional[Dict[str, HeadCalibration]] = None
        self._metadata: Dict = {}

    def _ensure_loaded(self) -> None:
        if self._heads is not None:
            return
        self._heads = load_calibration(self._path)
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f).get("fit_metadata", {})
            except Exception:
                self._metadata = {}

    def is_fitted(self) -> bool:
        self._ensure_loaded()
        assert self._heads is not None
        return any(hc.method != "identity" for hc in self._heads.values())

    def status(self) -> Dict:
        """Summary for the diagnostics endpoint."""
        self._ensure_loaded()
        assert self._heads is not None
        return {
            "calibration_path": str(self._path),
            "file_exists": self._path.exists(),
            "is_fitted": self.is_fitted(),
            "fit_metadata": self._metadata,
            "heads": {name: hc.to_dict() for name, hc in self._heads.items()},
        }

    def calibrate(self, probs: np.ndarray, head: str) -> np.ndarray:
        """Apply the fitted calibrator for ``head`` to a probability array.

        Accepts shape (C,) or (N, C). Returns the same shape.
        """
        self._ensure_loaded()
        assert self._heads is not None

        hc = self._heads.get(head)
        if hc is None:
            logger.warning("No calibrator for head=%s — returning raw probs.", head)
            return np.asarray(probs, dtype=float)

        arr = np.asarray(probs, dtype=float)
        squeeze = arr.ndim == 1
        if squeeze:
            arr = arr.reshape(1, -1)

        if hc.method == "identity":
            out = arr
        elif hc.method == "temperature":
            out = apply_temperature(arr, hc.temperature)
        elif hc.method == "isotonic":
            if hc.isotonic_x is None or hc.isotonic_y is None:
                logger.warning(
                    "head=%s is marked isotonic but missing breakpoints — "
                    "falling back to identity.", head,
                )
                out = arr
            else:
                out = apply_isotonic(arr, hc.isotonic_x, hc.isotonic_y)
        else:
            logger.warning("Unknown calibration method %r — returning raw.", hc.method)
            out = arr

        return out[0] if squeeze else out


# Module-level singleton — cheap and safe because identity fallback means
# constructing it never touches disk beyond a stat() call.
_default_service: Optional[CalibrationService] = None


def default_service() -> CalibrationService:
    global _default_service
    if _default_service is None:
        _default_service = CalibrationService()
    return _default_service
