"""
MC-Dropout Bayesian uncertainty service.

Why this module exists
----------------------
Previously the MC-Dropout logic lived inside ``routes/synthetic/uncertainty_router.py``.
That worked fine for a single endpoint, but Phase 1 needs the same primitive from:

  * trajectory forecasting (uncertainty bands over a 14-day horizon)
  * counterfactual engine   (risk-delta with confidence intervals)
  * dashboard intelligence  (per-day reliability flags)

Duplicating the MC-Dropout toggle + entropy math three more times would be a
correctness bug waiting to happen. This module is the single source of truth.

Model-safety guarantees
-----------------------
* We NEVER modify the loaded model's weights.
* We ONLY toggle ``torch.nn.Dropout`` modules into train-mode (leaving BatchNorm,
  LayerNorm, etc. in eval-mode). This is the exact procedure from Gal &
  Ghahramani (2016) — any deviation breaks the Bayesian interpretation.
* We ALWAYS restore ``model.eval()`` in a ``finally`` block, so a mid-flight
  exception cannot leave the model in train mode for the next request.
* All computation is done under ``torch.no_grad()`` — no gradients tracked.

Interpretation
--------------
``predictive_entropy``   — total uncertainty (aleatoric + epistemic).
``expected_entropy``     — mean per-sample entropy (aleatoric component).
``mutual_information``   — MI = predictive_entropy - expected_entropy, isolates
                           the *epistemic* (model) uncertainty. High MI means
                           the model disagrees with itself → more data or a
                           different architecture would help. Low MI with high
                           predictive entropy means the ambiguity is in the
                           data itself (aleatoric) and more data won't help.
``prediction_stability`` — fraction of MC samples that argmax-agree with the
                           point estimate. <0.5 = unreliable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

# Numerical-stability floor for log-probability computations.
# log(0) is undefined; we clip probabilities up to ``_EPS`` before taking logs.
_EPS = 1e-10


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
    """Result of a single MC-Dropout forward sweep on a 3-class risk LSTM."""
    n_samples: int
    point_probabilities: List[float]       # dropout-OFF point estimate
    point_class: int
    mean_probabilities: List[float]        # mean across MC samples
    class_statistics: List[ClassStatistic]
    predictive_entropy: float
    expected_entropy: float                # aleatoric proxy
    mutual_information: float              # epistemic proxy
    prediction_stability: float            # agreement with point estimate
    is_reliable: bool
    summary: str

    def to_dict(self) -> Dict:
        return {
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


# ── low-level dropout toggles ───────────────────────────────────────────────

def _enable_dropout(model: torch.nn.Module) -> None:
    """Flip only ``nn.Dropout`` modules into train-mode.

    Importantly we do NOT call ``model.train()`` — that would also flip
    BatchNorm and LayerNorm into training-statistics mode, which would corrupt
    the predictions even though the weights are frozen.
    """
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout):
            module.train()


def _restore_eval(model: torch.nn.Module) -> None:
    """Force the entire model back into eval mode. Safe to call multiple times."""
    model.eval()


# ── core sampler ────────────────────────────────────────────────────────────

def mc_dropout_probabilities(
    model: torch.nn.Module,
    dynamic_tensor: torch.Tensor,
    static_tensor: torch.Tensor,
    n_samples: int = 30,
) -> np.ndarray:
    """Draw N stochastic forward passes and return (N, num_classes) probabilities.

    The caller is responsible for putting tensors on the right device. We keep
    the function deliberately narrow so trajectory/counterfactual code can
    reuse it without paying the full statistics pipeline.
    """
    if model is None:
        raise RuntimeError("Risk model is not loaded")
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    probs_list: List[np.ndarray] = []
    try:
        _enable_dropout(model)
        for _ in range(n_samples):
            with torch.no_grad():
                logits = model(dynamic_tensor, static_tensor)
                probs = torch.softmax(logits, dim=1)
                probs_list.append(probs.cpu().numpy()[0])
    finally:
        # Guarantee cleanup even on CUDA OOM or other errors.
        _restore_eval(model)

    return np.stack(probs_list, axis=0)  # shape: (N, C)


# ── statistics helpers ──────────────────────────────────────────────────────

def _entropy(probs: np.ndarray) -> float:
    """Shannon entropy in nats. Accepts shape (C,) or (N, C)."""
    clipped = np.clip(probs, _EPS, 1.0)
    if clipped.ndim == 1:
        return float(-np.sum(clipped * np.log(clipped)))
    return float(np.mean(-np.sum(clipped * np.log(clipped), axis=1)))


def _summarise(
    point_class: int,
    class_names: Tuple[str, ...],
    stability: float,
    predictive_entropy: float,
    mc_preds: np.ndarray,
    n_samples: int,
) -> Tuple[bool, str]:
    """Decide reliability + render a one-paragraph human summary.

    Thresholds are tuned for 3-class risk:
      * stability > 0.7 AND predictive entropy < 1.0 → reliable.
      * stability > 0.5 → moderate.
      * otherwise → unreliable.
    The entropy ceiling of 1.0 nat ≈ 76% of max entropy for 3 classes.
    """
    is_reliable = stability > 0.7 and predictive_entropy < 1.0

    if is_reliable:
        msg = (
            f"The model is confident in its {class_names[point_class]} risk prediction. "
            f"{stability:.0%} of {n_samples} MC samples agree with the point estimate. "
            f"Predictive entropy is {predictive_entropy:.3f} (low)."
        )
    elif stability > 0.5:
        # Find the most common competing class among disagreeing samples.
        others = mc_preds[mc_preds != point_class]
        if others.size:
            runner_up = int(np.bincount(others, minlength=len(class_names)).argmax())
            msg = (
                f"The model shows moderate uncertainty. "
                f"{stability:.0%} of MC samples predict {class_names[point_class]}, "
                f"but {class_names[runner_up]} appears in some samples. "
                f"Consider additional data or clinical judgment."
            )
        else:
            msg = (
                f"The model shows moderate uncertainty. "
                f"{stability:.0%} of MC samples agree with the point estimate."
            )
    else:
        msg = (
            f"High uncertainty detected. Only {stability:.0%} of MC samples agree. "
            f"The model cannot reliably distinguish between risk classes for this "
            f"patient. Clinical judgment should take precedence."
        )
    return is_reliable, msg


# ── public API — the thing routers call ────────────────────────────────────

def predict_with_uncertainty(
    model: torch.nn.Module,
    dynamic_np: np.ndarray,
    static_np: np.ndarray,
    device: Optional[str] = None,
    n_samples: int = 30,
    class_names: Tuple[str, ...] = ("Low", "Medium", "High"),
    point_probabilities: Optional[List[float]] = None,
    point_class: Optional[int] = None,
) -> UncertaintyResult:
    """One-shot Bayesian risk prediction with full statistics.

    Parameters
    ----------
    model
        A frozen classification model compatible with
        ``model(dynamic_tensor, static_tensor) -> logits``.
    dynamic_np, static_np
        Numpy arrays from ``lib/synthetic/state_parser.parse_patient_state``.
    device
        Optional target device string. Defaults to whatever the model's
        first parameter is currently on.
    n_samples
        Number of MC samples. 30 is the sweet spot on RTX 3050 Ti — going
        higher adds noise-floor precision but doubles latency linearly.
    point_probabilities, point_class
        Optional pre-computed dropout-OFF estimate. Pass these to avoid a
        redundant forward pass if the caller already has them (e.g. the
        trajectory service computes per-day point risk anyway).
    """
    if device is None:
        # Use whatever device the model is parked on. Safer than guessing.
        try:
            device = next(model.parameters()).device  # type: ignore[assignment]
        except StopIteration:
            device = "cpu"

    dyn_t = torch.as_tensor(dynamic_np, dtype=torch.float32, device=device)
    stat_t = torch.as_tensor(static_np, dtype=torch.float32, device=device)

    # Step 1 — point estimate (optional, since trajectory already computes it)
    if point_probabilities is None or point_class is None:
        with torch.no_grad():
            _restore_eval(model)
            logits = model(dyn_t, stat_t)
            point_probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        point_probabilities = point_probs.tolist()
        point_class = int(np.argmax(point_probs))

    # Step 2 — MC samples
    all_probs = mc_dropout_probabilities(model, dyn_t, stat_t, n_samples=n_samples)
    mean_probs = all_probs.mean(axis=0)

    # Step 3 — per-class statistics
    num_classes = all_probs.shape[1]
    if len(class_names) != num_classes:
        # Fall back to integer labels if caller gave a mismatched name tuple.
        class_names = tuple(f"Class{i}" for i in range(num_classes))

    class_stats = [
        ClassStatistic(
            class_index=c,
            class_name=class_names[c],
            mean=round(float(mean_probs[c]), 4),
            std=round(float(all_probs[:, c].std()), 4),
            min=round(float(all_probs[:, c].min()), 4),
            max=round(float(all_probs[:, c].max()), 4),
        )
        for c in range(num_classes)
    ]

    # Step 4 — entropy decomposition
    predictive_entropy = _entropy(mean_probs)         # H[E[p]]
    expected_entropy = _entropy(all_probs)            # E[H[p]]
    mutual_information = max(0.0, predictive_entropy - expected_entropy)

    # Step 5 — stability
    mc_preds = np.argmax(all_probs, axis=1)
    stability = float(np.mean(mc_preds == point_class))

    is_reliable, summary = _summarise(
        point_class=point_class,
        class_names=class_names,
        stability=stability,
        predictive_entropy=predictive_entropy,
        mc_preds=mc_preds,
        n_samples=n_samples,
    )

    return UncertaintyResult(
        n_samples=n_samples,
        point_probabilities=[round(float(p), 4) for p in point_probabilities],
        point_class=int(point_class),
        mean_probabilities=[round(float(p), 4) for p in mean_probs.tolist()],
        class_statistics=class_stats,
        predictive_entropy=round(predictive_entropy, 4),
        expected_entropy=round(expected_entropy, 4),
        mutual_information=round(mutual_information, 4),
        prediction_stability=round(stability, 4),
        is_reliable=is_reliable,
        summary=summary,
    )
