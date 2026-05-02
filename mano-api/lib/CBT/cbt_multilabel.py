"""
Multi-distortion detection for the CBT classifier — pure-math core.

Motivation
----------
The existing Component 4 CBT pipeline runs a softmax over 11 classes
(10 cognitive distortions + "none") and returns the argmax. That's a
reasonable first cut, but journal entries rarely fit neatly into one
distortion: "I always mess things up and everyone will judge me for it"
is *both* overgeneralization ("always") AND mind-reading ("everyone will
judge me") AND possibly fortune-telling. The argmax collapses that
co-occurrence into a single label, under-representing the clinical
picture.

This module reinterprets the classifier's probability vector as a
multi-label signal: every class above a calibrated threshold counts,
subject to a min/max-count cap and a "none"-gate that respects the
classifier's own "no distortion detected" verdict.

Why keep it pure
----------------
Same rationale as ``lib.activity.gmm_selection`` — the selection logic
should be testable without loading the real MLP pickle. ``select_multi_
distortions`` takes a plain probability dict or array and returns a
plain list of labelled picks; everything else (text encoding, catalog
lookup, reframe template) belongs in the predictor/service layer.

Thresholds (clinical defaults)
------------------------------
* ``DEFAULT_THRESHOLD = 0.20`` — any class with >= 20% probability is
  considered present. Derived empirically from the validation cohort
  where a two-distortion entry typically had its secondary distortion
  in the 0.15-0.35 band.
* ``NONE_DOMINANCE = 0.50`` — if "none" has >= 50% probability AND is
  the argmax, we trust the classifier's "no distortion" verdict and
  return an empty picks list (saves the UI from false positives).
* ``MAX_DISTORTIONS_REPORTED = 3`` — more than three distortions in a
  single entry crosses into over-interpretation; three is the
  clinically defensible ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Union


# ── constants ──────────────────────────────────────────────────────────
DEFAULT_THRESHOLD = 0.20
NONE_DOMINANCE = 0.50
DEFAULT_MIN_DISTORTIONS = 1
DEFAULT_MAX_DISTORTIONS = 3
NONE_CLASS_NAME = "none"

# The full set of distortion classes the CBT MLP was trained on.
# Kept here as a reference so selection tests don't have to load the
# label encoder pickle. The predictor layer is still the source of
# truth at runtime — this list is only used by tests and diagnostics.
DISTORTION_CLASS_NAMES = (
    "catastrophizing",
    "black_and_white",
    "overgeneralization",
    "mind_reading",
    "fortune_telling",
    "emotional_reasoning",
    "should_statements",
    "labeling",
    "personalization",
    "discounting_positive",
    NONE_CLASS_NAME,
)


# ── dataclasses ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DistortionPick:
    """One line-item in the multi-label result."""
    distortion_type: str
    confidence: float
    rank: int              # 1-based rank within the result

    def to_dict(self) -> Dict:
        return {
            "distortion_type": self.distortion_type,
            "confidence": round(float(self.confidence), 4),
            "rank": int(self.rank),
        }


@dataclass(frozen=True)
class MultiLabelResult:
    """
    Structured multi-label output.

    ``is_none`` is true when the classifier confidently said "no
    distortion" (the NONE_DOMINANCE gate fired). In that case ``picks``
    is empty and the UI should show a "nothing flagged" message instead
    of a distortion card.
    """
    picks: List[DistortionPick]
    is_none: bool
    primary: Optional[DistortionPick]
    co_occurrence_strength: float
    threshold_used: float
    reason: str
    all_probabilities: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "picks": [p.to_dict() for p in self.picks],
            "is_none": bool(self.is_none),
            "primary": (self.primary.to_dict() if self.primary is not None else None),
            "co_occurrence_strength": round(float(self.co_occurrence_strength), 4),
            "threshold_used": round(float(self.threshold_used), 4),
            "reason": self.reason,
            "all_probabilities": {
                k: round(float(v), 4) for k, v in self.all_probabilities.items()
            },
            "count": len(self.picks),
        }


# ── input normalisation ────────────────────────────────────────────────
def _as_prob_dict(
    probs: Union[Dict[str, float], Sequence[float]],
    class_names: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """
    Normalise ``probs`` to ``{class_name: probability}``.

    Accepts either a dict keyed by class name, or a plain sequence
    paired with ``class_names`` (in the same order as the classifier's
    label encoder).
    """
    if isinstance(probs, dict):
        return {str(k): float(v) for k, v in probs.items()}

    if class_names is None:
        raise ValueError(
            "class_names is required when probs is a sequence"
        )
    prob_list = list(probs)
    names = list(class_names)
    if len(prob_list) != len(names):
        raise ValueError(
            f"probs has {len(prob_list)} entries but class_names has {len(names)}"
        )
    return {str(n): float(p) for n, p in zip(names, prob_list)}


def _validate_probs(prob_dict: Dict[str, float]) -> None:
    """Sanity-check the probability vector."""
    if not prob_dict:
        raise ValueError("probs is empty")
    total = 0.0
    for name, p in prob_dict.items():
        if p < 0.0 or p > 1.0 + 1e-6:
            raise ValueError(
                f"probability for class {name!r} out of [0, 1]: {p}"
            )
        total += p
    if abs(total - 1.0) > 0.05:
        # We allow a small tolerance because callers sometimes pass
        # an already-calibrated vector that doesn't sum exactly to 1.
        raise ValueError(
            f"probabilities must sum to ~1.0 (got {total:.4f}); "
            "ensure the softmax or calibrated output was passed"
        )


# ── selection logic ────────────────────────────────────────────────────
def select_multi_distortions(
    probs: Union[Dict[str, float], Sequence[float]],
    class_names: Optional[Sequence[str]] = None,
    threshold: float = DEFAULT_THRESHOLD,
    min_count: int = DEFAULT_MIN_DISTORTIONS,
    max_count: int = DEFAULT_MAX_DISTORTIONS,
    none_class: str = NONE_CLASS_NAME,
    none_dominance: float = NONE_DOMINANCE,
) -> MultiLabelResult:
    """
    Pick the set of distortions to report for a single journal entry.

    Algorithm
    ---------
    1. Normalise ``probs`` to a ``{name: prob}`` dict.
    2. If the "none" class has prob >= ``none_dominance`` AND is the
       argmax, return an empty picks list — we trust the classifier's
       "no distortion detected" verdict.
    3. Otherwise collect all non-"none" classes with prob >= threshold,
       sort descending by prob, cap at ``max_count``.
    4. If fewer than ``min_count`` survived the threshold, relax to
       the top ``min_count`` non-"none" classes by prob (so we always
       emit at least one pick when the model isn't sure enough about
       "none").
    5. Compute ``co_occurrence_strength`` = sum of picks' probabilities
       — a quick "how much distortion is in this entry overall" signal
       for the UI to gate a "multiple patterns detected" banner.
    """
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("threshold must be in [0, 1]")
    if min_count < 0:
        raise ValueError("min_count must be >= 0")
    if max_count < min_count:
        raise ValueError("max_count must be >= min_count")
    if none_dominance < 0.0 or none_dominance > 1.0:
        raise ValueError("none_dominance must be in [0, 1]")

    prob_dict = _as_prob_dict(probs, class_names)
    _validate_probs(prob_dict)

    # Argmax across every class (including "none")
    argmax_name = max(prob_dict.items(), key=lambda kv: kv[1])[0]
    argmax_prob = prob_dict[argmax_name]

    # "none" gate — trust a confident "no distortion" verdict
    none_prob = prob_dict.get(none_class, 0.0)
    if argmax_name == none_class and none_prob >= none_dominance:
        return MultiLabelResult(
            picks=[],
            is_none=True,
            primary=None,
            co_occurrence_strength=0.0,
            threshold_used=float(threshold),
            reason=(
                f"none_gate_fired: '{none_class}' p={none_prob:.2f} "
                f">= {none_dominance:.2f} and is argmax"
            ),
            all_probabilities=dict(prob_dict),
        )

    # Collect non-"none" picks sorted by prob descending
    ranked = sorted(
        ((name, p) for name, p in prob_dict.items() if name != none_class),
        key=lambda kv: (-kv[1], kv[0]),
    )

    # Threshold filter
    above_threshold = [(n, p) for n, p in ranked if p >= threshold]

    # min/max count enforcement
    if len(above_threshold) < min_count:
        picks_source = ranked[:min_count]
        reason = (
            f"threshold_relaxed: only {len(above_threshold)} classes "
            f">= {threshold:.2f}; returning top-{min_count} by prob"
        )
    else:
        picks_source = above_threshold[:max_count]
        reason = (
            f"threshold_applied: {len(above_threshold)} classes >= "
            f"{threshold:.2f}; reporting top-{min(max_count, len(above_threshold))}"
        )

    picks = [
        DistortionPick(distortion_type=name, confidence=prob, rank=i + 1)
        for i, (name, prob) in enumerate(picks_source)
    ]
    primary = picks[0] if picks else None
    co_strength = float(sum(p.confidence for p in picks))

    return MultiLabelResult(
        picks=picks,
        is_none=False,
        primary=primary,
        co_occurrence_strength=co_strength,
        threshold_used=float(threshold),
        reason=reason,
        all_probabilities=dict(prob_dict),
    )


# ── helper: categorise the multi-label result for the UI ──────────────
def classify_co_occurrence(result: MultiLabelResult) -> str:
    """
    Map a result to a one-word UI tag: ``none`` / ``single`` / ``pair``
    / ``cluster``. The frontend uses this to pick the right card layout
    without re-implementing the count logic.
    """
    if result.is_none or not result.picks:
        return "none"
    n = len(result.picks)
    if n == 1:
        return "single"
    if n == 2:
        return "pair"
    return "cluster"
