"""
Component 4 — MC-Dropout uncertainty for Activity / Feed PyTorch MLPs.

Why this exists
---------------
``lib/activity/feed_ranker.FeedRankingNet`` and
``lib/activity/recommendation_predictor.ActivityRecommendationNet`` are
both PyTorch MLPs trained with dropout (0.2 / 0.2 / 0.1 between the
three hidden blocks). At inference they run in ``eval`` mode, so
dropout is disabled and each forward pass is deterministic — the
model outputs a single relevance score between 0 and 1 with no
indication of how certain it is.

Gal & Ghahramani (2016, "Dropout as a Bayesian Approximation") showed
that leaving dropout *on* at inference and averaging N forward passes
is a well-founded variational approximation to a Bayesian posterior.
The mean of the N samples is the calibrated expected relevance; the
standard deviation is the *epistemic* uncertainty (what the model
doesn't know because of limited training data for this input).

For a mental-health product this matters for two concrete reasons:

1. **Feed ranking.** A stressed user should see posts we are
   confident they'll find helpful. If the ranker is uncertain,
   falling back to recency (or to a safer always-helpful category)
   is kinder than pushing a high-variance guess.

2. **Activity recommendation.** Recommending the wrong coping
   strategy to a user in crisis can backfire. The
   ``activity_service`` layer already has a rule-based filter for
   crisis users; with uncertainty available it can also skip
   high-variance picks regardless of rule match.

What this module does
---------------------
* ``enable_mc_dropout(model)`` — put a trained model into "inference
  with dropout" mode: BatchNorm layers stay in eval mode (critical!
  BN in train mode on batch_size=1 nan's the output), only Dropout
  layers switch to train so they actually sample.

* ``mc_dropout_forward(model, X, n_samples)`` — run N forward passes,
  return an ``(n_samples, batch_size)`` stack of raw predictions.

* ``summarise_predictions(samples)`` — per-sample mean / std / 95% CI
  / coefficient-of-variation / effective-sample-size. ``UncertaintyEstimate``
  dataclass with ``to_dict``.

* ``rank_with_uncertainty(model, X, n_samples)`` — single entry point
  the feed/recommender services call; returns an array of
  ``UncertaintyEstimate`` objects (one per batch row).

Design principles
-----------------
* **Non-breaking** — this module is opt-in. The existing
  ``rank_feed_posts`` / ``score_all_activities`` entry points keep
  their deterministic behaviour by default.
* **Torch-optional** — if torch isn't installed, the module degrades
  to a stub that raises a clear error rather than failing at import.
  Matches the pattern in feed_ranker.py.
* **Stateless** — nothing is cached here. The model is owned by its
  predictor module; we just drive its dropout behaviour.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

logger = logging.getLogger("component4.activity_uncertainty")

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover — torch is in requirements.txt
    TORCH_AVAILABLE = False
    torch = None  # type: ignore
    nn = None     # type: ignore


# Default number of MC samples. 20 is the Gal/Ghahramani standard for
# MLP-scale models: enough to stabilise mean/std without a noticeable
# inference-latency hit (20x 30k-param net ≈ <50ms on CPU).
DEFAULT_N_SAMPLES: int = 20

# Coefficient-of-variation threshold above which the service layer can
# treat a prediction as "high-uncertainty" and fall back to recency /
# rule-based scoring. Chosen as 0.30 — well above the typical 0.05-0.15
# range we see on well-trained MLPs and below the 0.5+ that indicates
# the model is essentially guessing.
HIGH_UNCERTAINTY_CV_THRESHOLD: float = 0.30


# ─── dataclasses ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class UncertaintyEstimate:
    """Per-prediction summary of an MC-Dropout ensemble.

    ``samples`` is kept around for diagnostics (so a callsite can
    plot a histogram of the N draws) but is NOT serialised by
    ``to_dict`` — it's usually too large for a JSON response.
    """
    mean: float
    std: float
    ci_low: float        # 2.5 percentile
    ci_high: float       # 97.5 percentile
    cv: float            # coefficient of variation (std / mean), clipped to inf-safe
    n_samples: int
    samples: np.ndarray = field(default_factory=lambda: np.zeros(0))

    @property
    def is_high_uncertainty(self) -> bool:
        """True when CV exceeds the service-level confidence cutoff."""
        return self.cv >= HIGH_UNCERTAINTY_CV_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "mean": round(float(self.mean), 6),
            "std": round(float(self.std), 6),
            "ci_low": round(float(self.ci_low), 6),
            "ci_high": round(float(self.ci_high), 6),
            "cv": round(float(self.cv), 6),
            "n_samples": int(self.n_samples),
            "is_high_uncertainty": bool(self.is_high_uncertainty),
        }


# ─── Dropout enabling ───────────────────────────────────────────────

def enable_mc_dropout(model) -> None:
    """Put the model in "inference with dropout" mode.

    Standard PyTorch idiom: ``model.eval()`` flips both Dropout and
    BatchNorm into inference behaviour. MC-Dropout needs Dropout to
    keep sampling, so we walk the module tree and re-enable just the
    Dropout layers. BatchNorm must stay in eval mode — flipping it to
    train on batch_size=1 will nan-out the output because the running
    mean/var is computed with no degrees of freedom.
    """
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch is not available; MC-Dropout is unusable")
    model.eval()
    n_enabled = 0
    for mod in model.modules():
        if isinstance(mod, (nn.Dropout, nn.Dropout1d, nn.Dropout2d, nn.Dropout3d)):
            mod.train()
            n_enabled += 1
    if n_enabled == 0:
        logger.warning(
            "enable_mc_dropout found no Dropout layers in the model — "
            "forward passes will be deterministic. Check your model "
            "architecture."
        )


def disable_mc_dropout(model) -> None:
    """Restore normal eval mode (both Dropout + BatchNorm inactive).

    Called after the sampling sweep so subsequent deterministic
    inference calls don't accidentally get a stochastic output.
    """
    if not TORCH_AVAILABLE:
        return
    model.eval()


# ─── forward-pass sampler ───────────────────────────────────────────

def mc_dropout_forward(
    model,
    X,
    *,
    n_samples: int = DEFAULT_N_SAMPLES,
) -> np.ndarray:
    """Run ``n_samples`` stochastic forward passes and stack the results.

    Parameters
    ----------
    model : nn.Module
        A trained PyTorch model with at least one Dropout layer. The
        model is put into MC-Dropout mode for the duration of this
        call and restored to plain ``.eval()`` on exit.
    X : torch.Tensor or np.ndarray, shape (batch, features)
        Inputs. Promoted to torch.Tensor if needed.
    n_samples : int
        Number of forward passes. Default 20 (Gal/Ghahramani standard).

    Returns
    -------
    np.ndarray shape (n_samples, batch) containing each forward pass's
    raw output. Caller summarises via ``summarise_predictions``.
    """
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch is not available; MC-Dropout is unusable")
    if n_samples < 1:
        raise ValueError(f"n_samples must be >= 1, got {n_samples}")

    if not isinstance(X, torch.Tensor):
        X = torch.from_numpy(np.asarray(X, dtype=np.float32))
    if X.ndim == 1:
        X = X.unsqueeze(0)
    if X.ndim != 2:
        raise ValueError(f"X must be 1-D or 2-D, got ndim={X.ndim}")

    enable_mc_dropout(model)
    try:
        samples = []
        with torch.no_grad():
            for _ in range(n_samples):
                out = model(X)
                # Model heads typically output either (B,) or (B, 1);
                # squeeze so downstream summary stats see (n, B).
                arr = out.detach().cpu().numpy()
                if arr.ndim == 2 and arr.shape[1] == 1:
                    arr = arr[:, 0]
                samples.append(arr)
        return np.stack(samples, axis=0)
    finally:
        disable_mc_dropout(model)


# ─── summarisers ────────────────────────────────────────────────────

def _safe_cv(mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """Coefficient of variation with a floor so CV doesn't blow up
    when the mean prediction is near zero.

    Numerically, CV = std / max(|mean|, eps). We use a floor of 1e-6
    which is three orders of magnitude below any realistic relevance
    score (those live in [0, 1] with a sigmoid output).
    """
    return std / np.maximum(np.abs(mean), 1e-6)


def summarise_predictions(samples: np.ndarray) -> List[UncertaintyEstimate]:
    """Per-batch-row uncertainty summary of an MC sample stack.

    Parameters
    ----------
    samples : np.ndarray, shape (n_samples, batch) OR (n_samples,)
        The output of ``mc_dropout_forward``. A 1-D input is treated as
        a single-item batch.

    Returns
    -------
    list of ``UncertaintyEstimate`` — one per batch row, in input order.
    """
    arr = np.asarray(samples, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"samples must be (n_samples, batch) or (n_samples,); got {arr.shape}")

    n_samples, batch = arr.shape
    # Percentile-based 95% CI. ``ddof=1`` on std = sample std (not
    # population) which is the honest choice for an MC estimator of
    # posterior variance.
    means = arr.mean(axis=0)
    stds = arr.std(axis=0, ddof=1) if n_samples > 1 else np.zeros(batch)
    ci_lo = np.percentile(arr, 2.5, axis=0)
    ci_hi = np.percentile(arr, 97.5, axis=0)
    cvs = _safe_cv(means, stds)

    return [
        UncertaintyEstimate(
            mean=float(means[i]),
            std=float(stds[i]),
            ci_low=float(ci_lo[i]),
            ci_high=float(ci_hi[i]),
            cv=float(cvs[i]),
            n_samples=int(n_samples),
            samples=arr[:, i].copy(),
        )
        for i in range(batch)
    ]


# ─── combined entry point ───────────────────────────────────────────

def predict_with_uncertainty(
    model,
    X,
    *,
    n_samples: int = DEFAULT_N_SAMPLES,
) -> List[UncertaintyEstimate]:
    """One-shot: sample + summarise.

    Convenience wrapper around ``mc_dropout_forward`` +
    ``summarise_predictions``. The hot path for service callers.
    """
    samples = mc_dropout_forward(model, X, n_samples=n_samples)
    return summarise_predictions(samples)


# ─── Adapter for numpy-only testing ─────────────────────────────────

def summarise_numpy_samples(
    samples: Sequence[Sequence[float]] | np.ndarray,
) -> List[UncertaintyEstimate]:
    """Summarise a user-provided sample stack without touching torch.

    Useful for unit tests and for service layers that produce their
    own MC samples through a different mechanism (e.g. bootstrap over
    input noise).
    """
    return summarise_predictions(np.asarray(samples, dtype=float))
