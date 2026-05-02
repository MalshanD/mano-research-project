"""
Component 2 — Bayesian uncertainty service for the risk predictor.

Why this exists
---------------
Calibration (``lib/assesment/calibrator.py``) makes the model's probabilities
*trustworthy on average*. Uncertainty answers the orthogonal question:
*how sure is the model about THIS patient?*. Two patients can have the same
calibrated 72/100 depression score but wildly different uncertainty — one
driven by an unambiguous signal, the other sitting on a knife-edge between
"moderate" and "high". Clinicians need to distinguish the two.

Design — why not just reuse ``lib/synthetic/uncertainty_service``?
-----------------------------------------------------------------
That module is PyTorch-specific (it toggles ``torch.nn.Dropout`` modules
into train-mode). Component 2 runs a frozen Keras Dense NN, so we need a
Keras-native path. The mathematical primitives — entropy decomposition,
predictive entropy vs expected entropy, mutual information, stability —
are identical and we keep the vocabulary matching on purpose so the
Component 1 and Component 2 results share a reporting vocabulary.

Two sampling strategies
-----------------------
1. **MC-Dropout (Gal & Ghahramani, 2016)** — preferred. If the frozen
   Keras model has dropout layers, we force them active by calling the
   model with ``training=True`` on each stochastic forward pass. We do
   NOT call ``model.trainable = True`` or fit() — only the TF graph
   path is flipped, so weights are untouched and batchnorm statistics
   are unaffected. Matches Gal & Ghahramani exactly.

2. **Input-perturbation fallback** — if the model has no dropout
   layers, MC-Dropout is a no-op and would silently return N identical
   copies of the point estimate. In that case we fall back to a small
   deterministic-noise ensemble: add Gaussian noise ``N(0, sigma)`` to
   each scaled feature row (sigma defaults to 0.05 on standard-scaled
   inputs ≈ one-twentieth of a standard deviation) and collect N
   forward passes. This is not "true Bayesian" — it's an input-
   perturbation sensitivity measure — but it produces a meaningful
   stability signal on otherwise-deterministic architectures and we
   flag the method used in the response so consumers can tell them
   apart.

What we compute (same as Component 1 for cross-service consistency):
  * predictive_entropy   — H[E[p]], total uncertainty
  * expected_entropy     — E[H[p]], aleatoric proxy
  * mutual_information   — MI = predictive - expected, epistemic proxy
  * prediction_stability — fraction of MC samples whose argmax matches
                           the point estimate
  * is_reliable          — stability > 0.7 AND predictive entropy < 1.0

Pure-numpy boundary
-------------------
Everything below the ``# ── Keras-specific hooks`` banner is pure numpy
and can be unit-tested without TensorFlow. The Keras hooks sit at the
very bottom and are imported lazily so importing this module does not
pull TF into processes that never need it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger("component2.uncertainty")

# Numerical stability floor for log-prob computations. Matches the value
# used in uncertainty_service.py and calibrator.py for consistency.
_EPS = 1e-10

# Default sampling method names — surfaced in responses so the frontend
# can show "mc_dropout (30 samples)" vs "input_perturbation (30 samples)".
METHOD_MC_DROPOUT = "mc_dropout"
METHOD_INPUT_PERTURBATION = "input_perturbation"
METHOD_DEGENERATE = "degenerate"  # N identical samples; no uncertainty signal

HEAD_NAMES = ("stress", "anxiety", "depression")
CLASS_NAMES = ("Low", "Moderate", "High")

# Default reliability thresholds — match Component 1 uncertainty_service
# so downstream consumers (dashboards, trajectory overlays) can treat
# is_reliable uniformly across both components.
DEFAULT_STABILITY_CUTOFF = 0.7
DEFAULT_ENTROPY_CUTOFF = 1.0
MODERATE_STABILITY_CUTOFF = 0.5


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClassStatistic:
    """Per-class aggregate over N MC samples."""
    class_index: int
    class_name: str
    mean: float
    std: float
    min: float
    max: float


@dataclass(frozen=True)
class UncertaintyResult:
    """Result of a full MC sweep for ONE head."""
    head: str
    method: str                          # METHOD_* constant
    n_samples: int
    point_probabilities: List[float]     # the deterministic (single-pass) estimate
    point_class: int
    mean_probabilities: List[float]      # mean across MC samples
    class_statistics: List[ClassStatistic]
    predictive_entropy: float
    expected_entropy: float              # aleatoric proxy
    mutual_information: float            # epistemic proxy
    prediction_stability: float          # fraction of MC samples agreeing with point
    is_reliable: bool
    summary: str

    def to_dict(self) -> Dict:
        return {
            "head": self.head,
            "method": self.method,
            "n_samples": self.n_samples,
            "point_probabilities": self.point_probabilities,
            "point_class": self.point_class,
            "mean_probabilities": self.mean_probabilities,
            "class_statistics": [cs.__dict__ for cs in self.class_statistics],
            "predictive_entropy": self.predictive_entropy,
            "expected_entropy": self.expected_entropy,
            "mutual_information": self.mutual_information,
            "prediction_stability": self.prediction_stability,
            "is_reliable": self.is_reliable,
            "summary": self.summary,
        }


# ─── Entropy + aggregation (pure numpy) ──────────────────────────────────────

def entropy(probs: np.ndarray) -> float:
    """Shannon entropy in nats. Accepts shape (C,) or (N, C).

    For (N, C) inputs we return the *mean* per-row entropy — this is the
    standard ``E[H[p]]`` used in the aleatoric/epistemic decomposition.
    """
    clipped = np.clip(np.asarray(probs, dtype=float), _EPS, 1.0)
    if clipped.ndim == 1:
        return float(-np.sum(clipped * np.log(clipped)))
    return float(np.mean(-np.sum(clipped * np.log(clipped), axis=1)))


def _reliability_summary(
    head: str,
    point_class: int,
    class_names: Sequence[str],
    stability: float,
    predictive_entropy: float,
    mc_preds: np.ndarray,
    n_samples: int,
) -> Tuple[bool, str]:
    """Reliability decision + human-readable summary string.

    Thresholds match ``lib/synthetic/uncertainty_service`` so a patient
    flagged "unreliable" in Component 1 reads the same as in Component 2.
    """
    is_reliable = (
        stability > DEFAULT_STABILITY_CUTOFF
        and predictive_entropy < DEFAULT_ENTROPY_CUTOFF
    )
    cname = class_names[point_class] if point_class < len(class_names) else f"class{point_class}"

    if is_reliable:
        msg = (
            f"{head.capitalize()} risk prediction is confident — "
            f"{stability:.0%} of {n_samples} MC samples agree on {cname}. "
            f"Predictive entropy {predictive_entropy:.3f} (low)."
        )
    elif stability > MODERATE_STABILITY_CUTOFF:
        others = mc_preds[mc_preds != point_class]
        if others.size:
            runner_up_idx = int(np.bincount(others, minlength=len(class_names)).argmax())
            runner_up = (
                class_names[runner_up_idx]
                if runner_up_idx < len(class_names)
                else f"class{runner_up_idx}"
            )
            msg = (
                f"{head.capitalize()} risk shows moderate uncertainty — "
                f"{stability:.0%} of MC samples predict {cname}, but "
                f"{runner_up} appears in the remainder. Consider additional "
                f"context or clinical review before acting on borderline scores."
            )
        else:
            msg = (
                f"{head.capitalize()} risk shows moderate uncertainty — "
                f"stability {stability:.0%}."
            )
    else:
        msg = (
            f"High uncertainty detected for {head}. Only {stability:.0%} of "
            f"MC samples agree on a class; the model cannot reliably "
            f"distinguish between risk levels for this patient. Clinical "
            f"judgement should take precedence."
        )
    return is_reliable, msg


def aggregate_mc_samples(
    head: str,
    samples: np.ndarray,
    method: str,
    point_probabilities: Optional[Sequence[float]] = None,
    class_names: Sequence[str] = CLASS_NAMES,
) -> UncertaintyResult:
    """Turn a raw ``(N, C)`` MC-sample array into a full ``UncertaintyResult``.

    ``point_probabilities`` — optional pre-computed deterministic estimate.
    When omitted we use ``samples.mean(axis=0)`` as the point estimate,
    which is the usual MC-Dropout convention.
    """
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 2:
        raise ValueError("samples must be shape (N, C)")
    n_samples, num_classes = samples.shape
    if n_samples < 1:
        raise ValueError("at least one MC sample required")

    mean_probs = samples.mean(axis=0)
    if point_probabilities is None:
        point_probs = mean_probs
    else:
        point_probs = np.asarray(point_probabilities, dtype=float)
        if point_probs.shape != (num_classes,):
            raise ValueError(
                f"point_probabilities shape {point_probs.shape} != "
                f"expected ({num_classes},)"
            )
    point_class = int(np.argmax(point_probs))

    # Per-class statistics across MC samples.
    class_stats: List[ClassStatistic] = []
    for c in range(num_classes):
        name = class_names[c] if c < len(class_names) else f"class{c}"
        class_stats.append(ClassStatistic(
            class_index=c,
            class_name=name,
            mean=round(float(mean_probs[c]), 4),
            std=round(float(samples[:, c].std()), 4),
            min=round(float(samples[:, c].min()), 4),
            max=round(float(samples[:, c].max()), 4),
        ))

    # Entropy decomposition.
    predictive_entropy = entropy(mean_probs)         # H[E[p]]
    expected_entropy = entropy(samples)              # E[H[p]]
    mutual_information = max(0.0, predictive_entropy - expected_entropy)

    # Argmax-stability — fraction of samples whose argmax matches the point.
    mc_preds = samples.argmax(axis=1)
    stability = float(np.mean(mc_preds == point_class))

    is_reliable, summary = _reliability_summary(
        head=head,
        point_class=point_class,
        class_names=class_names,
        stability=stability,
        predictive_entropy=predictive_entropy,
        mc_preds=mc_preds,
        n_samples=n_samples,
    )

    return UncertaintyResult(
        head=head,
        method=method,
        n_samples=int(n_samples),
        point_probabilities=[round(float(p), 4) for p in point_probs],
        point_class=point_class,
        mean_probabilities=[round(float(p), 4) for p in mean_probs],
        class_statistics=class_stats,
        predictive_entropy=round(float(predictive_entropy), 4),
        expected_entropy=round(float(expected_entropy), 4),
        mutual_information=round(float(mutual_information), 4),
        prediction_stability=round(stability, 4),
        is_reliable=is_reliable,
        summary=summary,
    )


# ─── Sampling strategies (model-agnostic, test-friendly) ─────────────────────
#
# These helpers are deliberately shaped around callable abstractions so
# tests can inject deterministic fake predictors without importing TF.

PredictFn = Callable[[np.ndarray], Sequence[np.ndarray]]
"""A function that maps scaled features (shape (1, F)) to a sequence of
per-head probability arrays, each shape (1, C). Matches the contract of
``keras.Model.__call__`` applied to a 3-head Keras output."""


def input_perturbation_samples(
    predict_fn: PredictFn,
    scaled_row: np.ndarray,
    n_samples: int,
    sigma: float = 0.05,
    rng: Optional[np.random.Generator] = None,
) -> List[np.ndarray]:
    """Collect N forward passes over a Gaussian-perturbed input row.

    Returns a list of length n_heads, each array shape (N, C). We batch
    the n_samples perturbations into a single ``(N, F)`` feature matrix
    so we get one model call instead of N.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if scaled_row.ndim == 2 and scaled_row.shape[0] == 1:
        base = scaled_row[0]
    elif scaled_row.ndim == 1:
        base = scaled_row
    else:
        raise ValueError("scaled_row must be shape (F,) or (1, F)")

    rng = rng or np.random.default_rng()
    perturbed = base[None, :] + rng.normal(0.0, sigma, size=(n_samples, base.shape[0]))
    outputs = predict_fn(perturbed)  # Sequence of (N, C) arrays — one per head.
    return [np.asarray(o, dtype=float) for o in outputs]


def mc_dropout_samples(
    dropout_predict_fn: PredictFn,
    scaled_row: np.ndarray,
    n_samples: int,
) -> List[np.ndarray]:
    """Collect N MC-Dropout forward passes by repeatedly calling the
    model-with-dropout-active callable.

    Unlike input-perturbation we can't batch the samples — dropout noise
    needs a fresh stochastic mask per pass — so this loops.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if scaled_row.ndim == 1:
        scaled_row = scaled_row[None, :]
    elif scaled_row.ndim != 2 or scaled_row.shape[0] != 1:
        raise ValueError("scaled_row must be shape (F,) or (1, F)")

    head_samples: Optional[List[List[np.ndarray]]] = None
    for _ in range(n_samples):
        out = dropout_predict_fn(scaled_row)
        if head_samples is None:
            head_samples = [[] for _ in out]
        for h, arr in enumerate(out):
            arr = np.asarray(arr, dtype=float)
            # Each call gives us (1, C); we want to stack to (N, C).
            head_samples[h].append(arr[0] if arr.ndim == 2 else arr)

    assert head_samples is not None
    return [np.stack(h, axis=0) for h in head_samples]


def is_degenerate(samples: np.ndarray, atol: float = 1e-6) -> bool:
    """True if every MC sample is (numerically) identical — i.e. the
    sampling strategy collapsed and the MC ensemble carries no
    information beyond the point estimate."""
    if samples.shape[0] < 2:
        return True
    return bool(np.allclose(samples, samples[0][None, :], atol=atol))


# ─── Keras-specific hooks (imported lazily) ──────────────────────────────────

def keras_has_dropout(model) -> bool:
    """Return True if the Keras model contains at least one Dropout layer.

    Lives here so the router / predictor can pick MC-Dropout vs input
    perturbation without re-importing tensorflow. We only touch
    ``model.layers`` which is pure-Python metadata.
    """
    if model is None:
        return False
    try:
        layers = getattr(model, "layers", None)
        if layers is None:
            return False
        for layer in layers:
            if layer.__class__.__name__ in ("Dropout", "SpatialDropout1D",
                                             "SpatialDropout2D", "AlphaDropout"):
                return True
            # Walk nested Sequential/Functional sub-models too.
            sub = getattr(layer, "layers", None)
            if sub:
                for inner in sub:
                    if inner.__class__.__name__ in ("Dropout", "SpatialDropout1D",
                                                     "SpatialDropout2D", "AlphaDropout"):
                        return True
    except Exception:  # pragma: no cover — defensive
        return False
    return False


def build_keras_predictors(model) -> Tuple[PredictFn, PredictFn]:
    """Return ``(deterministic_fn, stochastic_fn)`` bound to a Keras model.

    * ``deterministic_fn(x)`` — one forward pass with dropout OFF
      (``training=False``). Matches normal ``model.predict`` behaviour.
    * ``stochastic_fn(x)``    — one forward pass with dropout ON
      (``training=True``). Reruns MC-Dropout while leaving weights frozen.

    Returns numpy arrays so downstream code stays TF-agnostic.
    """
    def _deterministic(x: np.ndarray) -> List[np.ndarray]:
        out = model(x, training=False)
        return [o.numpy() if hasattr(o, "numpy") else np.asarray(o) for o in out]

    def _stochastic(x: np.ndarray) -> List[np.ndarray]:
        out = model(x, training=True)
        return [o.numpy() if hasattr(o, "numpy") else np.asarray(o) for o in out]

    return _deterministic, _stochastic
