"""
Component 4 — Cold-start handling & diversity re-ranking for Activity Recommender.

Why this exists
---------------
The PyTorch recommender scores every activity against a 7-dimensional
user profile (stress / anxiety / depression / body / behavior /
emotional / social, each 0-100). Two recurring production issues:

1. **Cold start.** New users land on the home screen before completing
   any assessment, so the profile is empty / all-None / all-zero.
   The model was trained on realistic profiles; feeding it zeros
   collapses the score distribution (every activity looks equally
   relevant) and the top-N list becomes arbitrary.

2. **Category monoculture.** The model is internally consistent: if a
   user scores high on anxiety, every "anxiety_relief" activity gets a
   high relevance. Without a diversity step the top-10 ends up being
   "deep breathing", "4-7-8 breathing", "box breathing", "diaphragmatic
   breathing"... which is boring UX and misses the cross-modal benefit
   of physical + social + mindful coping in combination.

This module adds two small, pure-Python primitives that plug into
``recommendation_predictor.score_all_activities`` via optional
kwargs — no change in behaviour when the flags are off.

Cold-start
~~~~~~~~~~
``COLD_START_PROFILE`` is a mild-distress population prior (derived
from the Component 1 assessment histograms: stress/anxiety/depression
~50, wellness dims ~55). ``is_cold_start`` detects "all missing or all
zero"; ``apply_cold_start_defaults`` fills the gaps non-destructively.

Diversity (MMR)
~~~~~~~~~~~~~~~
We use Maximal Marginal Relevance (Carbonell & Goldstein, SIGIR 1998):

    MMR(i) = λ · rel(i) - (1 - λ) · max_{j ∈ selected} sim(i, j)

``λ = 1`` → pure relevance (identity). ``λ = 0`` → pure diversity (round-
robin across categories). For this product we default to ``λ = 0.7``
when enabled — still relevance-led but one or two mindfulness picks
won't monopolise the top-5.

Similarity is a simple category + target-conditions Jaccard. This
keeps MMR pure-numpy, interpretable, and cheap (≤ 100 activities × top-k).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Cold-start priors
# ---------------------------------------------------------------------------
# Population prior for users with no assessment data yet. Slightly above
# "none" on the distress dimensions so crisis/escalation rules don't fire,
# and moderate on the wellness dimensions so nothing gets artificially
# penalised. Source: Component 1 assessment distribution (median over
# the MANO synthetic training set).
COLD_START_PROFILE = {
    "stress_score": 50.0,
    "anxiety_score": 50.0,
    "depression_score": 40.0,
    "body_score": 55.0,
    "behavior_score": 55.0,
    "emotional_score": 50.0,
    "social_score": 50.0,
}

# When all seven scores fall below this threshold we treat the profile
# as "no signal" and apply the cold-start prior. 5.0 is deliberately
# conservative — a real user who scored a 3 on every axis in the
# assessment is a valid observation, not a cold start.
_COLD_START_THRESHOLD = 5.0


def is_cold_start(user_scores: dict) -> bool:
    """Return True if the profile carries no usable signal.

    A profile is cold-start if every score is either missing (``None``),
    non-numeric, or below :data:`_COLD_START_THRESHOLD`.
    """
    if not user_scores:
        return True

    any_signal = False
    for key in COLD_START_PROFILE:
        raw = user_scores.get(key)
        if raw is None:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val >= _COLD_START_THRESHOLD:
            any_signal = True
            break
    return not any_signal


def apply_cold_start_defaults(user_scores: Optional[dict]) -> dict:
    """Return a copy of ``user_scores`` with missing dims filled from the prior.

    Never overwrites a present numeric value; just fills holes. Accepts
    ``None`` as input (common when the caller hasn't loaded a profile
    yet) and returns the full prior.
    """
    if not user_scores:
        return dict(COLD_START_PROFILE)

    filled = dict(user_scores)
    for key, default in COLD_START_PROFILE.items():
        raw = filled.get(key)
        if raw is None:
            filled[key] = default
            continue
        try:
            float(raw)
        except (TypeError, ValueError):
            filled[key] = default
    return filled


# ---------------------------------------------------------------------------
# Diversity (MMR)
# ---------------------------------------------------------------------------

DEFAULT_MMR_LAMBDA = 0.7  # relevance-led; 0.3 weight on diversity
DEFAULT_MMR_TOP_K = 20


@dataclass(frozen=True)
class _ActivityFingerprint:
    category: str
    conditions: frozenset
    problems: frozenset


def _fingerprint(activity: dict) -> _ActivityFingerprint:
    return _ActivityFingerprint(
        category=str(activity.get("category", "")),
        conditions=frozenset(activity.get("target_conditions", []) or []),
        problems=frozenset(activity.get("target_problems", []) or []),
    )


def _similarity(a: _ActivityFingerprint, b: _ActivityFingerprint) -> float:
    """Symmetric similarity in [0, 1].

    Category match contributes 0.5 (categorical overlap dominates UX
    perception of "same kind of thing"). The remaining 0.5 is a Jaccard
    over target conditions + problems — so "two stress-relief activities
    that both target the same underlying problem" are more similar than
    "two stress-relief activities that address different problems".
    """
    cat_sim = 1.0 if a.category and a.category == b.category else 0.0

    tags_a = a.conditions | a.problems
    tags_b = b.conditions | b.problems
    if tags_a or tags_b:
        inter = len(tags_a & tags_b)
        union = len(tags_a | tags_b)
        jaccard = inter / union if union else 0.0
    else:
        jaccard = 0.0

    return 0.5 * cat_sim + 0.5 * jaccard


def mmr_rerank(
    results: list,
    *,
    lambda_diversity: float = DEFAULT_MMR_LAMBDA,
    top_k: int = DEFAULT_MMR_TOP_K,
) -> list:
    """Re-rank ``results`` in-place-safe using Maximal Marginal Relevance.

    ``results`` is the list returned by ``score_all_activities``:
    each element must have ``relevance_score`` (0-100) and an
    ``activity`` dict with ``category`` / ``target_conditions`` /
    ``target_problems``.

    Only the first ``top_k`` positions are re-ordered — everything past
    that is left in relevance order (it'll be clipped by paging anyway,
    and re-ranking 100 items when the UI only shows 10 is wasteful).

    Returns a new list. Each re-ranked element gains an ``mmr_score``
    field for debugging. No-ops (returns the original order) when
    ``lambda_diversity`` is 1.0 or ``len(results) <= 1``.
    """
    if not results or len(results) <= 1:
        return list(results)

    lam = float(lambda_diversity)
    if lam >= 1.0:
        # Pure relevance = no re-ranking.
        return list(results)
    lam = max(lam, 0.0)

    k = min(max(int(top_k), 1), len(results))
    pool = list(results[:k])
    tail = list(results[k:])

    # Normalise relevance to [0, 1] so it's on the same scale as
    # similarity. Avoid divide-by-zero if every item scored 0.
    max_rel = max((float(r.get("relevance_score", 0.0)) for r in pool), default=0.0)
    norm = max_rel if max_rel > 0 else 1.0

    fingerprints = [_fingerprint(r.get("activity", {})) for r in pool]

    selected_idx: list[int] = []
    remaining_idx = set(range(len(pool)))

    while remaining_idx:
        best_idx = None
        best_mmr = -float("inf")

        for i in remaining_idx:
            rel = float(pool[i].get("relevance_score", 0.0)) / norm

            if selected_idx:
                max_sim = max(
                    _similarity(fingerprints[i], fingerprints[j])
                    for j in selected_idx
                )
            else:
                max_sim = 0.0

            mmr = lam * rel - (1.0 - lam) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i

        if best_idx is None:  # defensive: set semantics guarantee this won't hit
            break
        pool[best_idx]["mmr_score"] = round(best_mmr, 4)
        selected_idx.append(best_idx)
        remaining_idx.discard(best_idx)

    reranked_head = [pool[i] for i in selected_idx]
    return reranked_head + tail


# ---------------------------------------------------------------------------
# Convenience: single entry point for the service layer
# ---------------------------------------------------------------------------

def prepare_user_scores(
    user_scores: Optional[dict],
    *,
    with_cold_start_fallback: bool = True,
) -> tuple[dict, bool]:
    """Return (effective_scores, was_cold_start).

    Combines detection + filling so the caller just does:

        scores, cold = prepare_user_scores(raw, with_cold_start_fallback=True)
    """
    if not with_cold_start_fallback:
        return (user_scores or {}), False
    cold = is_cold_start(user_scores or {})
    if cold:
        return dict(COLD_START_PROFILE), True
    return apply_cold_start_defaults(user_scores), False


__all__ = [
    "COLD_START_PROFILE",
    "DEFAULT_MMR_LAMBDA",
    "DEFAULT_MMR_TOP_K",
    "apply_cold_start_defaults",
    "is_cold_start",
    "mmr_rerank",
    "prepare_user_scores",
]
