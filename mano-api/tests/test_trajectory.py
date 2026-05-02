"""
Tests for ``lib.assesment.trajectory`` — the Risk Trajectory Tracking core.

All tests are pure-numpy: no DB, no Keras, no FastAPI client. Scenarios are
hand-crafted time series that exercise each of the six states, the
worsening-in-low projection, sparse-data branches, and the gap-reset rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import pytest

from lib.assesment import trajectory as T
from lib.assesment.trajectory import (
    DEFAULT_GAP_RESET_DAYS,
    DEFAULT_WINDOW_SIZE,
    HIGH_RISK_EVENT_THRESHOLD,
    LABEL_HIGH,
    LABEL_LOW,
    LABEL_MODERATE,
    LOW_THRESHOLD,
    MIN_SESSIONS_FOR_TREND,
    MODERATE_THRESHOLD,
    RAPID_WORSENING_SLOPE,
    STABLE_BAND_POINTS,
    STATE_ESTABLISHING_BASELINE,
    STATE_IMPROVING,
    STATE_RAPIDLY_WORSENING,
    STATE_RECOVERING,
    STATE_SLOWLY_WORSENING,
    STATE_STABLE,
    STATE_VOLATILE,
    VOLATILITY_STD_POINTS,
    WORSENING_PROJECTION_DAYS,
    SessionPoint,
    analyse_all_conditions,
    analyse_condition,
    classify_trajectory,
    compute_slope,
    derive_metrics,
    level_for_score,
    project_crosses_threshold,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


BASE = datetime(2026, 4, 1)


def _weekly(scores: List[float], start: datetime = BASE) -> List[SessionPoint]:
    """Build a list of SessionPoints one week apart starting at ``start``."""
    return [SessionPoint(start + timedelta(days=7 * i), float(s))
            for i, s in enumerate(scores)]


# ─── level_for_score ────────────────────────────────────────────────────────


class TestLevelForScore:
    def test_below_low_threshold_is_low(self):
        assert level_for_score(0) == LABEL_LOW
        assert level_for_score(34.999) == LABEL_LOW

    def test_at_low_threshold_is_moderate(self):
        # Strict inequality: score >= 35 ⇒ Moderate.
        assert level_for_score(LOW_THRESHOLD) == LABEL_MODERATE

    def test_between_thresholds_is_moderate(self):
        assert level_for_score(50) == LABEL_MODERATE
        assert level_for_score(MODERATE_THRESHOLD - 0.001) == LABEL_MODERATE

    def test_at_moderate_threshold_is_high(self):
        assert level_for_score(MODERATE_THRESHOLD) == LABEL_HIGH
        assert level_for_score(95) == LABEL_HIGH


# ─── compute_slope ──────────────────────────────────────────────────────────


class TestComputeSlope:
    def test_empty_history_is_zero(self):
        assert compute_slope([]) == 0.0

    def test_single_point_is_zero(self):
        assert compute_slope(_weekly([40])) == 0.0

    def test_linear_up_matches_expected_pts_per_week(self):
        # +5 points per week.
        slope = compute_slope(_weekly([10, 15, 20, 25]))
        assert slope == pytest.approx(5.0, rel=1e-6)

    def test_linear_down_is_negative(self):
        slope = compute_slope(_weekly([50, 45, 40, 35]))
        assert slope == pytest.approx(-5.0, rel=1e-6)

    def test_flat_is_zero(self):
        assert compute_slope(_weekly([30, 30, 30, 30])) == pytest.approx(0.0, abs=1e-9)

    def test_same_day_collapses_to_zero(self):
        # All points at the same timestamp should not explode polyfit.
        pts = [SessionPoint(BASE, s) for s in [20, 30, 40]]
        assert compute_slope(pts) == 0.0

    def test_uses_time_weighting_not_index_spacing(self):
        # Two points a single week apart jumping 20 points = 20 pts/week,
        # NOT an average over many indices.
        pts = [SessionPoint(BASE, 10.0), SessionPoint(BASE + timedelta(days=7), 30.0)]
        assert compute_slope(pts) == pytest.approx(20.0, rel=1e-6)


# ─── classify_trajectory ────────────────────────────────────────────────────


class TestClassifyTrajectory:
    def test_empty_gives_baseline(self):
        assert classify_trajectory([], 0.0) == STATE_ESTABLISHING_BASELINE

    def test_single_point_gives_baseline(self):
        assert classify_trajectory(_weekly([40]), 0.0) == STATE_ESTABLISHING_BASELINE

    def test_stable_when_all_within_band(self):
        pts = _weekly([50, 52, 51, 49])  # span 3 points, inside ±5
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_STABLE

    def test_slowly_worsening_moderate_slope(self):
        pts = _weekly([20, 24, 28, 32])  # +4 pts/week, under RAPID cutoff
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_SLOWLY_WORSENING

    def test_rapidly_worsening_steep_slope(self):
        pts = _weekly([20, 30, 40, 55])  # ~11 pts/week
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_RAPIDLY_WORSENING

    def test_improving_when_trending_down(self):
        pts = _weekly([40, 35, 30, 25])  # -5 pts/week
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_IMPROVING

    def test_recovering_after_moderate_peak(self):
        # Peak hit 75 (High), now coming down — should read as Recovering.
        pts = _weekly([75, 68, 55, 45])
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_RECOVERING

    def test_volatile_when_big_swings(self):
        # Std dev easily exceeds the VOLATILITY_STD_POINTS cutoff.
        pts = _weekly([30, 60, 25, 65])
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_VOLATILE

    def test_volatile_beats_stable_when_both_could_match(self):
        # High std but small net slope and peak under Moderate — this is
        # the canonical "chaotic, not a clean up/down story" case, which
        # should be reported as Volatile rather than coerced into Stable
        # or a direction bucket.
        pts = _weekly([15, 50, 10, 35])
        assert classify_trajectory(pts, compute_slope(pts)) == STATE_VOLATILE


# ─── project_crosses_threshold ──────────────────────────────────────────────


class TestProjectCrossesThreshold:
    def test_positive_slope_crosses(self):
        # At 32 with +4 pts/week and 14-day horizon → 32 + 8 = 40 ≥ 35 ⇒ True.
        assert project_crosses_threshold(32.0, 4.0, 35.0, 14) is True

    def test_slow_slope_does_not_cross(self):
        # +1 pt/week over 14 days = +2 points, won't cross.
        assert project_crosses_threshold(32.0, 1.0, 35.0, 14) is False

    def test_negative_slope_never_crosses(self):
        assert project_crosses_threshold(32.0, -5.0, 35.0, 14) is False

    def test_already_past_threshold_returns_false(self):
        # We only fire the flag when currently BELOW the threshold.
        assert project_crosses_threshold(50.0, 2.0, 35.0, 14) is False


# ─── derive_metrics ─────────────────────────────────────────────────────────


class TestDeriveMetrics:
    def test_empty_history_returns_zeros(self):
        m = derive_metrics([], [], 0.0)
        assert m.peak_score == 0.0
        assert m.peak_timestamp is None
        assert m.days_since_last_high is None
        assert m.change_since_last is None

    def test_peak_reflects_all_history_not_just_window(self):
        all_points = _weekly([80, 40, 30, 25, 20])  # peak at index 0
        window = all_points[-3:]                     # window misses the peak
        m = derive_metrics(all_points, window, -2.5)
        assert m.peak_score == 80.0
        assert m.peak_timestamp == all_points[0].timestamp.isoformat()

    def test_days_since_last_high_is_none_when_no_high(self):
        all_points = _weekly([20, 25, 30, 32])
        m = derive_metrics(all_points, all_points, 4.0)
        assert m.days_since_last_high is None

    def test_days_since_last_high_measured_from_latest(self):
        # Last high-risk event was 3 weeks before latest.
        pts = _weekly([80, 30, 25, 20])
        m = derive_metrics(pts, pts, -20.0)
        assert m.days_since_last_high == 21  # 3 weeks

    def test_change_since_last_reflects_latest_delta(self):
        pts = _weekly([20, 22, 30])
        m = derive_metrics(pts, pts, 5.0)
        assert m.change_since_last == pytest.approx(8.0)

    def test_recovery_speed_only_when_falling_from_moderate_peak(self):
        falling = _weekly([75, 60, 45, 30])
        m = derive_metrics(falling, falling, -15.0)
        assert m.recovery_speed_per_week == pytest.approx(15.0)

    def test_recovery_speed_none_when_peak_is_latest_point(self):
        # Peak is the current session → we haven't started recovering.
        pts = _weekly([30, 45, 60, 75])
        m = derive_metrics(pts, pts, 15.0)
        assert m.recovery_speed_per_week is None

    def test_stability_index_zero_for_flat_window(self):
        pts = _weekly([40, 40, 40, 40])
        m = derive_metrics(pts, pts, 0.0)
        assert m.stability_index == 0.0

    def test_stability_index_larger_for_swingy_window(self):
        swingy = _weekly([10, 60, 10, 60])
        flat = _weekly([40, 42, 41, 40])
        m_swingy = derive_metrics(swingy, swingy, compute_slope(swingy))
        m_flat = derive_metrics(flat, flat, compute_slope(flat))
        assert m_swingy.stability_index > m_flat.stability_index


# ─── analyse_condition — full-stack behaviour ──────────────────────────────


class TestAnalyseCondition:
    def test_zero_sessions_gives_baseline(self):
        r = analyse_condition("stress", [])
        assert r.state == STATE_ESTABLISHING_BASELINE
        assert r.confidence == "baseline"
        assert r.current_score is None
        assert r.current_level is None
        assert r.alert is None
        assert r.worsening_in_low_flag is False

    def test_one_session_gives_baseline_with_current_score(self):
        r = analyse_condition("anxiety", _weekly([42]))
        assert r.state == STATE_ESTABLISHING_BASELINE
        assert r.confidence == "baseline"
        assert r.current_score == 42.0
        assert r.current_level == LABEL_MODERATE

    def test_two_sessions_low_confidence(self):
        r = analyse_condition("stress", _weekly([30, 40]))
        assert r.confidence == "low"
        assert r.sessions_used == 2

    def test_three_sessions_high_confidence(self):
        r = analyse_condition("stress", _weekly([30, 40, 50]))
        assert r.confidence == "high"

    def test_worsening_in_low_flag_and_alert(self):
        # Exact scenario from the spec: still labelled Low but drifting upward.
        pts = _weekly([20, 24, 28, 32])
        r = analyse_condition("depression", pts)
        assert r.current_level == LABEL_LOW
        assert r.worsening_in_low_flag is True
        assert r.alert is not None
        assert "Moderate" in r.alert
        assert "Low" in r.alert

    def test_worsening_in_moderate_does_not_fire_low_flag(self):
        # Already above Low — the flag is specifically for the Low-range case.
        pts = _weekly([50, 55, 60, 65])
        r = analyse_condition("stress", pts)
        assert r.worsening_in_low_flag is False
        assert r.current_level == LABEL_MODERATE

    def test_rapidly_worsening_emits_alert(self):
        pts = _weekly([20, 35, 50, 70])  # huge slope
        r = analyse_condition("stress", pts)
        assert r.state == STATE_RAPIDLY_WORSENING
        assert r.alert is not None
        assert "rapidly" in r.alert.lower()

    def test_stable_has_no_alert(self):
        pts = _weekly([50, 52, 51, 49])
        r = analyse_condition("stress", pts)
        assert r.state == STATE_STABLE
        assert r.alert is None

    def test_sessions_worsening_counts_consecutive_rises(self):
        pts = _weekly([20, 24, 28, 32])
        r = analyse_condition("depression", pts)
        # 3 consecutive rises: 20→24, 24→28, 28→32.
        assert r.sessions_worsening == 3

    def test_sessions_worsening_zero_when_last_delta_negative(self):
        pts = _weekly([20, 30, 40, 35])  # last delta is -5
        r = analyse_condition("stress", pts)
        assert r.sessions_worsening == 0

    def test_gap_reset_trims_pre_gap_history(self):
        # 53-day gap between session 2 and 3 → pre-gap points ignored.
        pts = [
            SessionPoint(BASE, 60.0),
            SessionPoint(BASE + timedelta(days=7), 65.0),
            # 53-day gap: exceeds DEFAULT_GAP_RESET_DAYS=42
            SessionPoint(BASE + timedelta(days=60), 20.0),
            SessionPoint(BASE + timedelta(days=67), 22.0),
            SessionPoint(BASE + timedelta(days=74), 25.0),
        ]
        r = analyse_condition("depression", pts)
        # Only 3 post-gap points should feed the window slope.
        assert r.sessions_used == 3
        # But peak still reflects the FULL history (65 before the gap).
        assert r.metrics.peak_score == 65.0

    def test_gap_reset_disabled_when_gap_short(self):
        # 10-day gap — well below the 42-day threshold.
        pts = [
            SessionPoint(BASE, 20.0),
            SessionPoint(BASE + timedelta(days=7), 25.0),
            SessionPoint(BASE + timedelta(days=17), 30.0),
            SessionPoint(BASE + timedelta(days=24), 35.0),
        ]
        r = analyse_condition("stress", pts)
        assert r.sessions_used == 4  # Nothing trimmed.

    def test_out_of_order_points_are_sorted(self):
        # Scores 20 → 30 → 40 → 50 across 3 weeks = +10 pts/week,
        # fed in shuffled order. Sort defence must kick in.
        pts = [
            SessionPoint(BASE + timedelta(days=21), 50.0),
            SessionPoint(BASE, 20.0),
            SessionPoint(BASE + timedelta(days=7), 30.0),
            SessionPoint(BASE + timedelta(days=14), 40.0),
        ]
        r = analyse_condition("stress", pts)
        assert r.metrics.rate_of_change_per_week == pytest.approx(10.0, abs=0.5)
        # And the state should reflect the cleaned-up ordering.
        assert r.state == STATE_RAPIDLY_WORSENING

    def test_window_size_overrides_default(self):
        pts = _weekly([10, 15, 25, 50, 55])
        r = analyse_condition("stress", pts, window_size=2)
        # Only last 2 points feed the slope: (50, 55) → +5 pts/week.
        assert r.sessions_used == 2
        assert r.metrics.rate_of_change_per_week == pytest.approx(5.0, abs=0.5)

    def test_serialisable_to_dict(self):
        import json
        pts = _weekly([20, 24, 28, 32])
        r = analyse_condition("depression", pts)
        payload = r.to_dict()
        # Round-trip JSON to confirm no numpy/datetime leaks.
        json.loads(json.dumps(payload))
        assert payload["state"] == STATE_SLOWLY_WORSENING
        assert payload["worsening_in_low_flag"] is True
        assert "metrics" in payload

    def test_summary_mentions_head_name(self):
        r = analyse_condition("anxiety", _weekly([50, 52, 51, 49]))
        assert "Anxiety" in r.summary


# ─── analyse_all_conditions ────────────────────────────────────────────────


class TestAnalyseAllConditions:
    def test_returns_one_result_per_head(self):
        history = {
            "stress": _weekly([30, 35, 40]),
            "anxiety": _weekly([20, 22, 21]),
            "depression": _weekly([10, 12, 14, 16]),
        }
        out = analyse_all_conditions(history)
        assert set(out.keys()) == {"stress", "anxiety", "depression"}
        for head, r in out.items():
            assert r.head == head

    def test_handles_partial_history(self):
        # Only depression has any data — the other heads are empty.
        history = {
            "stress": [],
            "anxiety": [],
            "depression": _weekly([20, 24, 28, 32]),
        }
        out = analyse_all_conditions(history)
        assert out["stress"].state == STATE_ESTABLISHING_BASELINE
        assert out["anxiety"].state == STATE_ESTABLISHING_BASELINE
        assert out["depression"].worsening_in_low_flag is True


# ─── Module constants ──────────────────────────────────────────────────────


def test_thresholds_match_predictor_labels():
    # Must stay aligned with predictor._get_label. If one moves, the other
    # must move too — or the trajectory's "crossing into Moderate" will
    # disagree with the snapshot label.
    assert LOW_THRESHOLD == 35.0
    assert MODERATE_THRESHOLD == 70.0


def test_trajectory_states_are_unique_strings():
    states = {
        STATE_IMPROVING, STATE_STABLE, STATE_SLOWLY_WORSENING,
        STATE_RAPIDLY_WORSENING, STATE_RECOVERING, STATE_VOLATILE,
        STATE_ESTABLISHING_BASELINE,
    }
    assert len(states) == 7


def test_defaults_are_sensible():
    assert DEFAULT_WINDOW_SIZE >= MIN_SESSIONS_FOR_TREND
    assert DEFAULT_GAP_RESET_DAYS > 0
    assert RAPID_WORSENING_SLOPE > 0
    assert VOLATILITY_STD_POINTS > STABLE_BAND_POINTS
    assert WORSENING_PROJECTION_DAYS > 0
    assert HIGH_RISK_EVENT_THRESHOLD >= LOW_THRESHOLD
