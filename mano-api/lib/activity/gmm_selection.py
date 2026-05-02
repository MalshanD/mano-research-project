"""
Dynamic GMM cluster-count selection — pure-math core.

This module sits under the Keras/sklearn layer the same way
``lib.assesment.trajectory`` sits under the ORM layer for Component 2:
nothing in here touches a database, a trained model, or any sklearn
pickle on disk. Every function takes plain numbers in and returns plain
dataclasses/dicts out, so the selection logic can be unit-tested without
spinning up a sklearn fit.

What it does
------------
The existing Component 4 ships a GaussianMixture with K hardcoded to 5.
The master tech report flagged this as a known limitation: five clusters
is the right count *by convention* (Thriving / Stable / Growing /
Healing / Supported), not because the data agrees it's the right count.
Real user populations may pack into fewer, larger buckets or split into
more, finer ones; a K that's too large inflates the covariance matrices
and over-fits noise, a K that's too small smears clinically distinct
groups into the same bucket.

This module implements the standard information-criterion solution:
  * compute BIC/AIC/silhouette for every candidate K in a range,
  * pick the K that minimises BIC (preferred) or AIC,
  * break ties by silhouette,
  * apply a parsimony rule — if a smaller K is within a small ΔBIC
    of the winner, prefer the smaller K (Occam-style — the extra
    component isn't pulling its weight).

There's also a cluster-transition helper: given a per-session stream of
cluster assignments, collapse consecutive same-cluster runs into
``ClusterTransition`` events so the UI can show "you moved from Healing
to Growing on 2026-03-14". This is the Component 4 analogue of the
trajectory tracker's "direction-of-travel" signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


# ── constants ──────────────────────────────────────────────────────────
# Range of K we actually consider. 1 is meaningless (no clustering),
# 2 is rarely useful for a 7-dim space, and >8 starts over-fitting the
# small synthetic cohort Component 4 was trained on.
DEFAULT_MIN_K = 3
DEFAULT_MAX_K = 8

# Parsimony rule: if a smaller K has BIC within this many points of the
# best K, prefer the smaller K. Kass & Raftery (1995) call ΔBIC < 2
# "not worth more than a bare mention"; we pick 2 as the default.
DEFAULT_PARSIMONY_BIC_DELTA = 2.0

# How many covariance parameters a GMM component contributes for each
# ``covariance_type`` option sklearn supports. Exposed as a dict so the
# free-parameter count is testable without touching sklearn.
#   d = feature dimensionality
#   For ``full``:    d * (d + 1) / 2  covariance params per component
#   For ``tied``:    d * (d + 1) / 2  total (shared across components)
#   For ``diag``:    d                per component
#   For ``spherical``: 1              per component
COVARIANCE_PARAM_FORMULAS = ("full", "tied", "diag", "spherical")

# Minimum history length for per-user transition detection to emit a
# meaningful signal. Below this we still assign clusters but flag the
# result as "low confidence" so the UI doesn't claim a trend.
MIN_SESSIONS_FOR_TRANSITIONS = 2


# ── dataclasses ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CandidateScore:
    """
    Score-card for one K value in the sweep.

    ``silhouette`` is optional because it's undefined when the model
    collapses every sample into a single cluster (which can happen with
    degenerate covariance). In that case the caller should drop the
    candidate rather than pick it on BIC alone.
    """
    k: int
    bic: float
    aic: float
    log_likelihood: float
    n_free_params: int
    converged: bool
    silhouette: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "k": int(self.k),
            "bic": float(self.bic),
            "aic": float(self.aic),
            "log_likelihood": float(self.log_likelihood),
            "n_free_params": int(self.n_free_params),
            "converged": bool(self.converged),
            "silhouette": (None if self.silhouette is None
                           else float(self.silhouette)),
        }


@dataclass(frozen=True)
class SelectionResult:
    """
    Outcome of a full K-sweep + selection pass.

    ``selected_k`` is what the trainer should use; ``argmin_k`` is the
    raw minimum-BIC K before the parsimony rule kicks in. Keeping both
    lets the diagnostics endpoint surface the clinical reasoning ("we
    could have used 6, but 5 is within ΔBIC=2 and simpler").
    """
    selected_k: int
    argmin_k: int
    method: str              # "bic" | "aic"
    parsimony_applied: bool
    parsimony_delta: float
    candidates: List[CandidateScore]
    rejected: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "selected_k": int(self.selected_k),
            "argmin_k": int(self.argmin_k),
            "method": self.method,
            "parsimony_applied": bool(self.parsimony_applied),
            "parsimony_delta": float(self.parsimony_delta),
            "candidates": [c.to_dict() for c in self.candidates],
            "rejected": list(self.rejected),
        }


@dataclass(frozen=True)
class ClusterTransition:
    """One edge in the user's cluster journey."""
    from_cluster: int
    to_cluster: int
    from_community: str
    to_community: str
    at: datetime
    session_index: int       # 0-based index into the user's history

    def to_dict(self) -> Dict:
        return {
            "from_cluster": int(self.from_cluster),
            "to_cluster": int(self.to_cluster),
            "from_community": self.from_community,
            "to_community": self.to_community,
            "at": self.at.isoformat() if isinstance(self.at, datetime) else str(self.at),
            "session_index": int(self.session_index),
        }


# ── free-parameter counting ────────────────────────────────────────────
def count_gmm_free_params(
    k: int, n_features: int, covariance_type: str = "full",
) -> int:
    """
    Count a GaussianMixture's free parameters.

    This is what BIC and AIC penalise. sklearn computes it internally
    but doesn't export it as a stable API, so we reimplement the
    formulas here. The numbers match ``gmm._n_parameters()`` to within
    the off-by-one mixture-weight quirk (sklearn counts K-1 because the
    last weight is pinned by the sum-to-one constraint).

    See: Bishop, "Pattern Recognition and Machine Learning" §9.2.3.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if n_features < 1:
        raise ValueError("n_features must be >= 1")
    if covariance_type not in COVARIANCE_PARAM_FORMULAS:
        raise ValueError(
            f"covariance_type must be one of {COVARIANCE_PARAM_FORMULAS}, "
            f"got {covariance_type!r}"
        )

    # K-1 mixture weights (the last is pinned by sum-to-one)
    mean_params = k * n_features              # means, K × d
    weight_params = k - 1

    d = n_features
    if covariance_type == "full":
        cov_params = k * d * (d + 1) // 2
    elif covariance_type == "tied":
        cov_params = d * (d + 1) // 2
    elif covariance_type == "diag":
        cov_params = k * d
    else:  # spherical
        cov_params = k

    return int(mean_params + weight_params + cov_params)


# ── BIC / AIC arithmetic ───────────────────────────────────────────────
def compute_bic(log_likelihood: float, n_params: int, n_samples: int) -> float:
    """
    BIC = -2 ℓ + p · ln(N).

    Lower is better. ``log_likelihood`` is the *total* log-likelihood
    over the whole dataset (not a per-sample average).
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if n_params < 0:
        raise ValueError("n_params must be >= 0")
    import math
    return -2.0 * float(log_likelihood) + float(n_params) * math.log(n_samples)


def compute_aic(log_likelihood: float, n_params: int) -> float:
    """AIC = -2 ℓ + 2 p. Lower is better."""
    if n_params < 0:
        raise ValueError("n_params must be >= 0")
    return -2.0 * float(log_likelihood) + 2.0 * float(n_params)


# ── selection logic ────────────────────────────────────────────────────
def select_best_k(
    candidates: Sequence[CandidateScore],
    method: str = "bic",
    parsimony_delta: float = DEFAULT_PARSIMONY_BIC_DELTA,
    require_converged: bool = True,
) -> SelectionResult:
    """
    Pick the best K from a sweep.

    Algorithm
    ---------
    1. Filter out non-converged candidates (configurable).
    2. Pick ``argmin_k`` = K with smallest BIC (or AIC).
    3. Parsimony pass: among all candidates with score within
       ``parsimony_delta`` of argmin, prefer the smallest K. This is
       the "simpler-model-wins-ties" rule.
    4. Break remaining ties (same K pool at that depth) by silhouette
       when available, falling back to lower AIC if silhouette is
       missing for everyone in the pool.
    """
    if method not in ("bic", "aic"):
        raise ValueError(f"method must be 'bic' or 'aic', got {method!r}")
    if parsimony_delta < 0:
        raise ValueError("parsimony_delta must be >= 0")

    rejected: List[Dict] = []
    pool: List[CandidateScore] = []
    for c in candidates:
        if require_converged and not c.converged:
            rejected.append({
                "k": c.k,
                "reason": "did_not_converge",
                "bic": c.bic, "aic": c.aic,
            })
            continue
        pool.append(c)

    if not pool:
        raise ValueError(
            "no eligible candidates — all K values failed to converge, "
            "or the input list was empty"
        )

    def score(c: CandidateScore) -> float:
        return c.bic if method == "bic" else c.aic

    # argmin over the raw criterion
    argmin = min(pool, key=lambda c: (score(c), c.k))
    argmin_k = argmin.k
    argmin_score = score(argmin)

    # parsimony pool: every candidate within Δ of argmin
    parsimony_pool = [c for c in pool if (score(c) - argmin_score) <= parsimony_delta]

    # pick smallest K in the parsimony pool; tiebreak by silhouette (higher
    # is better) and then by AIC (lower is better)
    def parsimony_key(c: CandidateScore):
        sil = -c.silhouette if c.silhouette is not None else 0.0
        return (c.k, sil, c.aic)

    winner = min(parsimony_pool, key=parsimony_key)
    parsimony_applied = (winner.k != argmin_k)

    return SelectionResult(
        selected_k=winner.k,
        argmin_k=argmin_k,
        method=method,
        parsimony_applied=parsimony_applied,
        parsimony_delta=parsimony_delta,
        candidates=sorted(pool, key=lambda c: c.k),
        rejected=rejected,
    )


# ── cluster transition detection ───────────────────────────────────────
@dataclass(frozen=True)
class ClusterAssignment:
    """One session-level cluster assignment."""
    timestamp: datetime
    cluster_id: int
    community_name: str
    confidence: Optional[float] = None


def detect_transitions(
    assignments: Sequence[ClusterAssignment],
) -> List[ClusterTransition]:
    """
    Collapse a time-ordered sequence of cluster assignments into the
    list of actual transitions.

    Consecutive same-cluster assignments are merged — we only emit a
    ``ClusterTransition`` when the cluster changes. Input is assumed to
    be sorted oldest → newest; we re-sort defensively.
    """
    if not assignments:
        return []

    ordered = sorted(assignments, key=lambda a: a.timestamp)
    transitions: List[ClusterTransition] = []
    prev = ordered[0]
    for idx in range(1, len(ordered)):
        cur = ordered[idx]
        if cur.cluster_id != prev.cluster_id:
            transitions.append(ClusterTransition(
                from_cluster=prev.cluster_id,
                to_cluster=cur.cluster_id,
                from_community=prev.community_name,
                to_community=cur.community_name,
                at=cur.timestamp,
                session_index=idx,
            ))
        prev = cur

    return transitions


def summarise_journey(
    assignments: Sequence[ClusterAssignment],
) -> Dict:
    """
    Build a UI-ready summary of the user's cluster journey.

    Keys (stable):
      * ``total_sessions`` — how many snapshots we have
      * ``unique_clusters`` — count of distinct clusters visited
      * ``current_cluster`` / ``current_community`` — where they are now
      * ``transitions`` — list of ClusterTransition.to_dict()
      * ``transition_count``
      * ``low_confidence`` — true when total_sessions < threshold
      * ``most_common_community`` — modal cluster across history
    """
    if not assignments:
        return {
            "total_sessions": 0,
            "unique_clusters": 0,
            "current_cluster": None,
            "current_community": None,
            "transitions": [],
            "transition_count": 0,
            "low_confidence": True,
            "most_common_community": None,
        }

    ordered = sorted(assignments, key=lambda a: a.timestamp)
    latest = ordered[-1]
    transitions = detect_transitions(ordered)

    counts: Dict[str, int] = {}
    for a in ordered:
        counts[a.community_name] = counts.get(a.community_name, 0) + 1
    most_common = max(counts.items(), key=lambda kv: kv[1])[0]

    return {
        "total_sessions": len(ordered),
        "unique_clusters": len({a.cluster_id for a in ordered}),
        "current_cluster": int(latest.cluster_id),
        "current_community": latest.community_name,
        "transitions": [t.to_dict() for t in transitions],
        "transition_count": len(transitions),
        "low_confidence": len(ordered) < MIN_SESSIONS_FOR_TRANSITIONS,
        "most_common_community": most_common,
    }


# ── helper: candidate construction from raw metrics ────────────────────
def build_candidate(
    k: int,
    log_likelihood: float,
    n_samples: int,
    n_features: int,
    covariance_type: str = "full",
    converged: bool = True,
    silhouette: Optional[float] = None,
) -> CandidateScore:
    """
    Construct a ``CandidateScore`` from raw fit metrics.

    The offline trainer calls this after each GMM fit so the BIC/AIC
    numbers are computed once, centrally, and match what the selection
    layer uses (rather than relying on sklearn's internals).
    """
    n_params = count_gmm_free_params(k, n_features, covariance_type)
    return CandidateScore(
        k=k,
        bic=compute_bic(log_likelihood, n_params, n_samples),
        aic=compute_aic(log_likelihood, n_params),
        log_likelihood=float(log_likelihood),
        n_free_params=n_params,
        converged=bool(converged),
        silhouette=(None if silhouette is None else float(silhouette)),
    )
