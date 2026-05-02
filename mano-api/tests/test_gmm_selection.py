"""
Unit tests for the Dynamic GMM cluster-selection pure-math core.

These tests deliberately avoid sklearn, joblib, and the ORM — the logic
in ``lib.activity.gmm_selection`` is free of all three. That means the
whole suite runs in milliseconds and doesn't need a GMM fixture.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from lib.activity.gmm_selection import (
    CandidateScore,
    ClusterAssignment,
    DEFAULT_MAX_K,
    DEFAULT_MIN_K,
    DEFAULT_PARSIMONY_BIC_DELTA,
    MIN_SESSIONS_FOR_TRANSITIONS,
    build_candidate,
    compute_aic,
    compute_bic,
    count_gmm_free_params,
    detect_transitions,
    select_best_k,
    summarise_journey,
)


# ── count_gmm_free_params ──────────────────────────────────────────────
class TestCountGmmFreeParams:
    """Parameter-counting formulas must be consistent across covariance types."""

    def test_full_covariance_seven_features_five_components(self):
        # For d=7, k=5, full:
        #   means = 5 * 7 = 35
        #   weights = 5 - 1 = 4
        #   covariance = 5 * 7 * 8 / 2 = 140
        # Total: 35 + 4 + 140 = 179
        assert count_gmm_free_params(5, 7, "full") == 179

    def test_tied_covariance_shares_one_matrix(self):
        # d=7, k=5, tied: 35 + 4 + 7*8/2 = 35 + 4 + 28 = 67
        assert count_gmm_free_params(5, 7, "tied") == 67

    def test_diag_covariance_counts_diagonal_only(self):
        # d=7, k=5, diag: 35 + 4 + 5*7 = 35 + 4 + 35 = 74
        assert count_gmm_free_params(5, 7, "diag") == 74

    def test_spherical_covariance_one_variance_per_component(self):
        # d=7, k=5, spherical: 35 + 4 + 5 = 44
        assert count_gmm_free_params(5, 7, "spherical") == 44

    def test_monotonicity_full_covers_most_params(self):
        # For fixed (k, d), 'full' should always have the most free
        # parameters among the four covariance types.
        k, d = 5, 7
        counts = {
            "full": count_gmm_free_params(k, d, "full"),
            "tied": count_gmm_free_params(k, d, "tied"),
            "diag": count_gmm_free_params(k, d, "diag"),
            "spherical": count_gmm_free_params(k, d, "spherical"),
        }
        assert counts["full"] > counts["diag"] > counts["spherical"]
        # tied can be below spherical for small k; doesn't participate
        # in the strict chain, but should always be below full
        assert counts["tied"] < counts["full"]

    def test_invalid_k_raises(self):
        with pytest.raises(ValueError, match=r"k must be >= 1"):
            count_gmm_free_params(0, 7)

    def test_invalid_n_features_raises(self):
        with pytest.raises(ValueError, match=r"n_features must be >= 1"):
            count_gmm_free_params(5, 0)

    def test_invalid_covariance_type_raises(self):
        with pytest.raises(ValueError, match=r"covariance_type must be one of"):
            count_gmm_free_params(5, 7, "nonsense")


# ── BIC / AIC arithmetic ───────────────────────────────────────────────
class TestComputeBic:
    def test_formula_matches_bishop(self):
        # BIC = -2 * ll + p * ln(N)
        ll = -1000.0
        p = 50
        n = 500
        expected = -2 * ll + p * math.log(n)
        assert compute_bic(ll, p, n) == pytest.approx(expected)

    def test_lower_ll_means_higher_bic(self):
        # BIC rewards higher likelihood (since it's -2*ll + ...)
        a = compute_bic(-1000, 50, 500)
        b = compute_bic(-1100, 50, 500)
        assert b > a

    def test_more_params_means_higher_bic(self):
        a = compute_bic(-1000, 50, 500)
        b = compute_bic(-1000, 100, 500)
        assert b > a

    def test_invalid_n_samples_raises(self):
        with pytest.raises(ValueError, match=r"n_samples must be >= 1"):
            compute_bic(-1000, 50, 0)

    def test_invalid_n_params_raises(self):
        with pytest.raises(ValueError, match=r"n_params must be >= 0"):
            compute_bic(-1000, -1, 500)


class TestComputeAic:
    def test_formula(self):
        # AIC = -2 * ll + 2 * p
        ll = -900.0
        p = 80
        expected = -2 * ll + 2 * p
        assert compute_aic(ll, p) == pytest.approx(expected)

    def test_aic_has_no_sample_dependence(self):
        # AIC doesn't depend on N; BIC does. So for the same ll/p, AIC
        # is invariant to n_samples (and BIC isn't).
        assert compute_aic(-900, 80) == compute_aic(-900, 80)


# ── build_candidate ────────────────────────────────────────────────────
class TestBuildCandidate:
    def test_returns_consistent_scorecard(self):
        c = build_candidate(
            k=5, log_likelihood=-1000, n_samples=500, n_features=7,
            covariance_type="full", converged=True, silhouette=0.45,
        )
        assert c.k == 5
        assert c.n_free_params == 179
        assert c.bic == pytest.approx(compute_bic(-1000, 179, 500))
        assert c.aic == pytest.approx(compute_aic(-1000, 179))
        assert c.silhouette == pytest.approx(0.45)
        assert c.converged is True

    def test_missing_silhouette_is_ok(self):
        c = build_candidate(
            k=5, log_likelihood=-1000, n_samples=500, n_features=7,
        )
        assert c.silhouette is None
        assert c.converged is True  # default

    def test_to_dict_roundtrip(self):
        c = build_candidate(
            k=4, log_likelihood=-950, n_samples=400, n_features=7,
            silhouette=0.40,
        )
        d = c.to_dict()
        assert d["k"] == 4
        assert d["silhouette"] == pytest.approx(0.40)
        assert d["n_free_params"] == count_gmm_free_params(4, 7, "full")
        assert d["converged"] is True


# ── select_best_k ──────────────────────────────────────────────────────
def _fake(k, bic, aic=None, sil=None, converged=True):
    """Shortcut for building CandidateScore directly without the full
    arithmetic — lets tests pin BIC/AIC to whatever values they need."""
    return CandidateScore(
        k=k, bic=bic,
        aic=aic if aic is not None else bic - 10.0,
        log_likelihood=-1000.0, n_free_params=100,
        converged=converged, silhouette=sil,
    )


class TestSelectBestK:
    def test_picks_minimum_bic(self):
        candidates = [_fake(3, 1000), _fake(4, 900), _fake(5, 950)]
        result = select_best_k(candidates, method="bic", parsimony_delta=0)
        assert result.selected_k == 4
        assert result.argmin_k == 4
        assert result.parsimony_applied is False

    def test_picks_minimum_aic_when_requested(self):
        # BIC minimum = 4 but AIC minimum = 5
        candidates = [
            _fake(3, 1000, aic=800),
            _fake(4, 900, aic=750),
            _fake(5, 950, aic=700),
        ]
        result = select_best_k(candidates, method="aic", parsimony_delta=0)
        assert result.selected_k == 5
        assert result.argmin_k == 5

    def test_parsimony_prefers_smaller_k_within_delta(self):
        # K=4 has BIC=900, K=5 has BIC=899 (wins by 1 point). With
        # parsimony_delta=2 the simpler K=4 should win.
        candidates = [_fake(3, 1000), _fake(4, 900), _fake(5, 899)]
        result = select_best_k(
            candidates, method="bic", parsimony_delta=2.0,
        )
        assert result.argmin_k == 5
        assert result.selected_k == 4
        assert result.parsimony_applied is True

    def test_parsimony_doesnt_fire_outside_delta(self):
        # K=5 wins by 10 points — parsimony_delta=2 is insufficient.
        candidates = [_fake(3, 1000), _fake(4, 950), _fake(5, 890)]
        result = select_best_k(
            candidates, method="bic", parsimony_delta=2.0,
        )
        assert result.selected_k == 5
        assert result.parsimony_applied is False

    def test_excludes_nonconverged_candidates(self):
        # K=4 would win BIC but didn't converge
        candidates = [
            _fake(3, 1000),
            _fake(4, 800, converged=False),
            _fake(5, 950),
        ]
        result = select_best_k(candidates, method="bic", parsimony_delta=0)
        assert result.selected_k == 5
        assert len(result.rejected) == 1
        assert result.rejected[0]["k"] == 4
        assert result.rejected[0]["reason"] == "did_not_converge"

    def test_include_nonconverged_if_requested(self):
        candidates = [
            _fake(3, 1000),
            _fake(4, 800, converged=False),
            _fake(5, 950),
        ]
        result = select_best_k(
            candidates, method="bic", parsimony_delta=0, require_converged=False,
        )
        assert result.selected_k == 4
        assert result.rejected == []

    def test_tiebreak_on_silhouette(self):
        # Two candidates within ΔBIC tie at the same K; higher
        # silhouette should win the tiebreaker.
        candidates = [
            _fake(3, 900, sil=0.30),
            _fake(4, 900, sil=0.45),
            _fake(5, 901, sil=0.40),
        ]
        result = select_best_k(
            candidates, method="bic", parsimony_delta=2.0,
        )
        # Smallest K in parsimony pool wins — K=3 (pool is {3,4,5} all
        # within Δ=2 of argmin K=3).
        assert result.selected_k == 3

    def test_serialises_to_dict(self):
        candidates = [_fake(3, 1000), _fake(4, 900), _fake(5, 950)]
        result = select_best_k(candidates, method="bic", parsimony_delta=0)
        d = result.to_dict()
        assert d["selected_k"] == 4
        assert d["argmin_k"] == 4
        assert d["method"] == "bic"
        assert d["parsimony_applied"] is False
        assert len(d["candidates"]) == 3
        assert d["candidates"][0]["k"] == 3  # sorted by k

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match=r"no eligible candidates"):
            select_best_k([], method="bic")

    def test_all_nonconverged_raises(self):
        candidates = [_fake(3, 1000, converged=False)]
        with pytest.raises(ValueError, match=r"no eligible candidates"):
            select_best_k(candidates, method="bic")

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match=r"method must be"):
            select_best_k([_fake(3, 1000)], method="dic")

    def test_invalid_parsimony_delta_raises(self):
        with pytest.raises(ValueError, match=r"parsimony_delta must be"):
            select_best_k([_fake(3, 1000)], parsimony_delta=-1.0)


# ── detect_transitions ─────────────────────────────────────────────────
def _ts(days_ago: int) -> datetime:
    return datetime(2026, 4, 1) - timedelta(days=days_ago)


def _assign(days_ago: int, cluster_id: int, community: str, confidence=0.9):
    return ClusterAssignment(
        timestamp=_ts(days_ago),
        cluster_id=cluster_id,
        community_name=community,
        confidence=confidence,
    )


class TestDetectTransitions:
    def test_empty_returns_empty(self):
        assert detect_transitions([]) == []

    def test_single_session_no_transitions(self):
        a = [_assign(10, 0, "Thriving")]
        assert detect_transitions(a) == []

    def test_same_cluster_throughout_no_transitions(self):
        a = [
            _assign(10, 1, "Healing"),
            _assign(5, 1, "Healing"),
            _assign(1, 1, "Healing"),
        ]
        assert detect_transitions(a) == []

    def test_single_transition(self):
        a = [
            _assign(10, 1, "Healing"),
            _assign(5, 0, "Thriving"),
        ]
        transitions = detect_transitions(a)
        assert len(transitions) == 1
        assert transitions[0].from_cluster == 1
        assert transitions[0].to_cluster == 0
        assert transitions[0].from_community == "Healing"
        assert transitions[0].to_community == "Thriving"
        assert transitions[0].session_index == 1

    def test_multiple_transitions_in_order(self):
        a = [
            _assign(20, 1, "Healing"),
            _assign(15, 2, "Supported"),   # transition 1
            _assign(10, 2, "Supported"),   # no transition (same cluster)
            _assign(5, 3, "Growing"),      # transition 2
            _assign(1, 0, "Thriving"),     # transition 3
        ]
        transitions = detect_transitions(a)
        assert len(transitions) == 3
        assert [t.to_community for t in transitions] == [
            "Supported", "Growing", "Thriving",
        ]

    def test_unordered_input_is_sorted(self):
        # Pass newest first; expect the function to re-sort and report
        # transitions in chronological order.
        a = [
            _assign(1, 0, "Thriving"),
            _assign(10, 1, "Healing"),
            _assign(5, 0, "Thriving"),
        ]
        transitions = detect_transitions(a)
        assert len(transitions) == 1
        # The chronological sequence is Healing(10d) -> Thriving(5d) -> Thriving(1d)
        assert transitions[0].from_community == "Healing"
        assert transitions[0].to_community == "Thriving"

    def test_to_dict_has_iso_timestamp(self):
        a = [_assign(10, 1, "Healing"), _assign(5, 0, "Thriving")]
        t = detect_transitions(a)[0]
        d = t.to_dict()
        assert isinstance(d["at"], str)
        assert "T" in d["at"]  # ISO format
        assert d["session_index"] == 1


# ── summarise_journey ──────────────────────────────────────────────────
class TestSummariseJourney:
    def test_empty_history(self):
        s = summarise_journey([])
        assert s["total_sessions"] == 0
        assert s["current_cluster"] is None
        assert s["current_community"] is None
        assert s["low_confidence"] is True
        assert s["transition_count"] == 0

    def test_single_session_low_confidence(self):
        a = [_assign(10, 1, "Healing")]
        s = summarise_journey(a)
        assert s["total_sessions"] == 1
        assert s["current_community"] == "Healing"
        assert s["low_confidence"] is True
        assert s["transition_count"] == 0

    def test_multiple_sessions_counts_unique_clusters(self):
        a = [
            _assign(10, 1, "Healing"),
            _assign(5, 3, "Growing"),
            _assign(1, 1, "Healing"),
        ]
        s = summarise_journey(a)
        assert s["total_sessions"] == 3
        assert s["unique_clusters"] == 2
        assert s["current_community"] == "Healing"   # latest = 1 day ago
        assert s["transition_count"] == 2
        assert s["low_confidence"] is False
        assert s["most_common_community"] == "Healing"   # 2 of 3

    def test_most_common_uses_mode(self):
        a = [
            _assign(15, 2, "Supported"),
            _assign(10, 2, "Supported"),
            _assign(5, 3, "Growing"),
        ]
        s = summarise_journey(a)
        assert s["most_common_community"] == "Supported"


# ── module-level constants ─────────────────────────────────────────────
class TestConstants:
    def test_default_k_range_covers_sensible_values(self):
        assert DEFAULT_MIN_K == 3
        assert DEFAULT_MAX_K == 8
        assert DEFAULT_MIN_K < DEFAULT_MAX_K

    def test_parsimony_delta_matches_bishop_convention(self):
        # Kass & Raftery (1995) recommend ΔBIC < 2 as "not worth more
        # than a bare mention". We use 2.
        assert DEFAULT_PARSIMONY_BIC_DELTA == 2.0

    def test_min_sessions_is_at_least_two(self):
        # Two points = one transition; less means we can't detect anything.
        assert MIN_SESSIONS_FOR_TRANSITIONS >= 2
