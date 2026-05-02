"""
Component 4 — Per-feature explainability for the Feed Ranker.

Why this exists
---------------
The Feed Ranker MLP scores every post into a single 0-1 relevance and
the user sees the result without any indication of *why* the model
ranked one post over another. For a mental-health product two things
follow:

1. **Trust.** Users (and clinicians reviewing the system) need to be
   able to ask "why is this at the top of my feed?" and get a concrete
   answer that doesn't hand-wave with "the algorithm decided".

2. **Debugging.** Without per-feature attributions we can't tell
   whether the ranker is genuinely matching the user profile or
   leaning on a single dominant feature (e.g., recency drowning out
   relevance, or post_type one-hot trivially dominating text content).

What this module does
---------------------
Implements a simple, deterministic permutation-style attribution that
plugs into the existing ranker without retraining:

* For each feature group (user-score, post-type, text-feature group,
  recency) replace the live values with a neutral baseline (zeros for
  topic densities, "none" post-type, mid-recency) and re-run the model.
* The drop in score = the group's contribution to the original
  prediction. Positive Δ → the group pushed the relevance up;
  negative Δ → the group dragged it down.
* Top-k drivers (largest |Δ|) are attached to each post so the UI
  can render "Why this ranked high: matches your stress profile,
  posted recently".

This is **occlusion / leave-one-out attribution** — the cheapest
member of the SHAP family but trivially deterministic, well-suited to
tabular feature-group inputs, and fast (one extra forward pass per
group per post). For real SHAP shapley values we'd need ~|S|! coalitions
which is overkill for a 23-dim feature vector with natural group
structure.

Pure-numpy + torch — torch is optional; without it the explainer
gracefully reports `available=False` so the caller falls back to no
attributions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

try:
    import torch
    import torch.nn as _torch_nn  # noqa: F401 -- forces partial stubs to fail
    TORCH_AVAILABLE = True
except (ImportError, AttributeError):
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Feature group layout
# ---------------------------------------------------------------------------
# Mirrors feed_ranker.rank_feed_posts feature construction:
#   7 user scores + 5 post-type one-hot + 10 text features + 1 recency = 23
# Each tuple = (group_name, slice_start, slice_end_exclusive,
# baseline_values: np.ndarray of len (end-start)).

# Mid-scale baseline for user scores: 50/100. The model trained on
# scores in this range so 50 is a defensible "no signal" anchor.
_USER_SCORE_BASELINE = np.full(7, 50.0, dtype=np.float32)

# Post-type baseline: all zeros (i.e., no recognised type). The MLP
# treats "no type one-hot active" as a slight relevance reduction,
# which is appropriate for an attribution baseline.
_POST_TYPE_BASELINE = np.zeros(5, dtype=np.float32)

# Text features: zeros everywhere = an empty post (zero topic density,
# zero sentiment, zero word count). Same logic — no information.
_TEXT_FEATURE_BASELINE = np.zeros(10, dtype=np.float32)

# Recency baseline: mid-decay (~0.5). A "neither fresh nor stale" post.
_RECENCY_BASELINE = np.array([0.5], dtype=np.float32)

FEATURE_GROUPS: tuple = (
    ("user_profile", 0, 7, _USER_SCORE_BASELINE),
    ("post_type", 7, 12, _POST_TYPE_BASELINE),
    ("text_content", 12, 22, _TEXT_FEATURE_BASELINE),
    ("recency", 22, 23, _RECENCY_BASELINE),
)

# Human-readable labels for the UI, indexed by group name.
GROUP_LABELS = {
    "user_profile": "Matches your mental-health profile",
    "post_type": "Post type relevance",
    "text_content": "Topic match with your needs",
    "recency": "Recently posted",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupAttribution:
    """Contribution of one feature group to a single post's relevance.

    delta: signed score change from removing this group's signal
        (positive = group pushed score up; negative = group dragged
        score down). Range ≈ [-1, 1] since the model output is in [0, 1].
    abs_delta: |delta|, used for ranking driver importance.
    """
    group: str
    label: str
    delta: float
    abs_delta: float

    def to_dict(self) -> dict:
        return {
            "group": self.group,
            "label": self.label,
            "delta": round(float(self.delta), 4),
            "abs_delta": round(float(self.abs_delta), 4),
        }


# ---------------------------------------------------------------------------
# Core attribution
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Return True if torch is importable and the explainer can run."""
    return TORCH_AVAILABLE


def explain_prediction(
    model,
    scaler,
    base_features: np.ndarray,
    *,
    base_score: Optional[float] = None,
    top_k: int = 3,
) -> list:
    """Return ranked GroupAttribution list for a single 23-dim feature vector.

    Args:
        model: trained PyTorch MLP (FeedRankingNet). Must be in eval()
            mode — caller's responsibility (the singleton in
            feed_ranker.py is always in eval() after _load_model).
        scaler: sklearn-style scaler with .transform(np.ndarray) method.
            Same scaler the ranker uses on live inputs — applied to
            both the base and the ablated vectors so the model sees
            consistent units.
        base_features: shape (23,) raw (pre-scale) feature vector for
            one post. Order: user(7) + type(5) + text(10) + recency(1).
        base_score: optional precomputed model score on
            ``base_features`` — saves one forward pass when the caller
            already has it.
        top_k: how many drivers to keep (None = keep all).

    Returns:
        Sorted list of GroupAttribution (descending by abs_delta),
        clipped to ``top_k``. Empty list if torch isn't available or
        ``base_features`` has the wrong shape.
    """
    if not TORCH_AVAILABLE:
        return []
    if base_features.shape != (23,):
        return []

    # Materialise the base score if not provided.
    base = base_features.reshape(1, -1).astype(np.float32)
    if base_score is None:
        base_scaled = scaler.transform(base)
        with torch.no_grad():
            base_score = float(model(torch.FloatTensor(base_scaled)).item())

    attributions: list[GroupAttribution] = []
    for group_name, start, end, baseline in FEATURE_GROUPS:
        ablated = base.copy()
        ablated[0, start:end] = baseline
        ablated_scaled = scaler.transform(ablated)
        with torch.no_grad():
            ablated_score = float(model(torch.FloatTensor(ablated_scaled)).item())
        # delta = how much the group contributed: positive when the
        # full features score higher than the ablated features.
        delta = base_score - ablated_score
        attributions.append(
            GroupAttribution(
                group=group_name,
                label=GROUP_LABELS.get(group_name, group_name),
                delta=delta,
                abs_delta=abs(delta),
            )
        )

    attributions.sort(key=lambda a: a.abs_delta, reverse=True)
    if top_k is not None:
        attributions = attributions[: int(top_k)]
    return attributions


def explain_predictions_batch(
    model,
    scaler,
    feature_matrix: np.ndarray,
    base_scores: np.ndarray,
    *,
    top_k: int = 3,
) -> list:
    """Vectorised attribution over many posts.

    Avoids re-instantiating the FloatTensor for each post by building
    one big ablation matrix per group. For N posts and 4 groups, this
    is 4 forward passes total instead of 4*N.

    Args:
        feature_matrix: shape (N, 23) raw features.
        base_scores: shape (N,) live scores on ``feature_matrix``.

    Returns:
        list of length N, each a sorted-and-clipped list of
        GroupAttribution.
    """
    if not TORCH_AVAILABLE:
        return [[] for _ in range(len(base_scores))]
    if feature_matrix.ndim != 2 or feature_matrix.shape[1] != 23:
        return [[] for _ in range(len(base_scores))]

    n = feature_matrix.shape[0]
    base = feature_matrix.astype(np.float32)
    out: list[list[GroupAttribution]] = [[] for _ in range(n)]

    for group_name, start, end, baseline in FEATURE_GROUPS:
        ablated = base.copy()
        ablated[:, start:end] = baseline  # broadcast across all rows
        ablated_scaled = scaler.transform(ablated)
        with torch.no_grad():
            ablated_scores = (
                model(torch.FloatTensor(ablated_scaled)).cpu().numpy()
            )
        deltas = base_scores - ablated_scores  # shape (N,)

        for i, d in enumerate(deltas):
            out[i].append(
                GroupAttribution(
                    group=group_name,
                    label=GROUP_LABELS.get(group_name, group_name),
                    delta=float(d),
                    abs_delta=float(abs(d)),
                )
            )

    # Sort + clip per row.
    for i in range(n):
        out[i].sort(key=lambda a: a.abs_delta, reverse=True)
        if top_k is not None:
            out[i] = out[i][: int(top_k)]
    return out


__all__ = [
    "FEATURE_GROUPS",
    "GROUP_LABELS",
    "GroupAttribution",
    "explain_prediction",
    "explain_predictions_batch",
    "is_available",
]
