"""
Unit tests for the CBT multi-distortion selection logic.

The pure-math core in ``lib.activity.cbt_multilabel`` doesn't touch
the MLP pickle or the TF-IDF vectoriser — these tests feed it plain
probability dicts and assert on the picks / reason strings.
"""

from __future__ import annotations

import pytest

from lib.CBT.cbt_multilabel import (
    DEFAULT_MAX_DISTORTIONS,
    DEFAULT_MIN_DISTORTIONS,
    DEFAULT_THRESHOLD,
    DISTORTION_CLASS_NAMES,
    DistortionPick,
    MultiLabelResult,
    NONE_CLASS_NAME,
    NONE_DOMINANCE,
    classify_co_occurrence,
    select_multi_distortions,
)


# ── helpers ────────────────────────────────────────────────────────────
def _dict_probs(**overrides) -> dict:
    """Build a probability dict spanning all 11 classes, with overrides."""
    uniform = 0.02  # 10 non-"none" classes × 0.02 + 0.80 "none" = 1.0
    probs = {name: uniform for name in DISTORTION_CLASS_NAMES}
    probs[NONE_CLASS_NAME] = 0.80
    for k, v in overrides.items():
        probs[k] = v
    # renormalise so callers don't have to do the arithmetic
    total = sum(probs.values())
    return {k: v / total for k, v in probs.items()}


# ── single-distortion ───────────────────────────────────────────────────
class TestSinglePick:
    def test_clear_winner_returns_one_pick(self):
        probs = _dict_probs(catastrophizing=0.70, none=0.10)
        r = select_multi_distortions(probs)
        assert len(r.picks) == 1
        assert r.picks[0].distortion_type == "catastrophizing"
        assert r.is_none is False
        assert r.primary is not None
        assert r.primary.rank == 1

    def test_single_pick_has_co_occurrence_equal_to_confidence(self):
        probs = _dict_probs(catastrophizing=0.70, none=0.10)
        r = select_multi_distortions(probs)
        assert r.co_occurrence_strength == pytest.approx(r.picks[0].confidence)


# ── co-occurring distortions ───────────────────────────────────────────
class TestMultiPick:
    def test_two_above_threshold_both_reported(self):
        probs = _dict_probs(catastrophizing=0.40, overgeneralization=0.35, none=0.10)
        r = select_multi_distortions(probs)
        assert len(r.picks) == 2
        types = {p.distortion_type for p in r.picks}
        assert types == {"catastrophizing", "overgeneralization"}
        # ranks are assigned in descending-probability order
        assert r.picks[0].distortion_type == "catastrophizing"
        assert r.picks[0].rank == 1
        assert r.picks[1].rank == 2

    def test_max_count_cap_limits_output(self):
        probs = _dict_probs(
            catastrophizing=0.25, overgeneralization=0.22,
            mind_reading=0.21, fortune_telling=0.20, none=0.05,
        )
        r = select_multi_distortions(probs, max_count=2)
        assert len(r.picks) == 2

    def test_max_count_beats_min_count_when_min_exceeds_max(self):
        with pytest.raises(ValueError, match=r"max_count must be >= min_count"):
            select_multi_distortions(_dict_probs(), min_count=5, max_count=2)

    def test_three_plus_distortions_still_capped_at_max(self):
        probs = _dict_probs(
            catastrophizing=0.22, overgeneralization=0.21,
            mind_reading=0.20, fortune_telling=0.20, none=0.05,
        )
        r = select_multi_distortions(probs)  # max=3 by default
        assert len(r.picks) == 3


# ── "none" gate ────────────────────────────────────────────────────────
class TestNoneGate:
    def test_dominant_none_returns_empty_picks(self):
        probs = _dict_probs(catastrophizing=0.04, none=0.70)
        r = select_multi_distortions(probs)
        assert r.is_none is True
        assert r.picks == []
        assert r.primary is None
        assert "none_gate_fired" in r.reason
        assert r.co_occurrence_strength == 0.0

    def test_none_below_threshold_still_processes_distortions(self):
        # 'none' is below the 0.50 dominance cutoff, so we should
        # still report distortions above threshold.
        probs = _dict_probs(catastrophizing=0.55, none=0.30)
        r = select_multi_distortions(probs)
        assert r.is_none is False
        assert len(r.picks) >= 1
        assert r.picks[0].distortion_type == "catastrophizing"

    def test_none_high_but_not_argmax(self):
        # 'none' is above the dominance threshold but another class
        # is even higher — we should still treat a distortion as present.
        probs = _dict_probs(catastrophizing=0.55, none=0.51)
        # renormalise because the helper added extras; but 0.55 > 0.51
        r = select_multi_distortions(probs)
        assert r.is_none is False
        assert r.picks[0].distortion_type == "catastrophizing"

    def test_custom_none_dominance_threshold(self):
        # Explicit probability dict (no renormalisation). 'none' is the
        # argmax at 0.40, which is below the default 0.50 dominance
        # threshold — so the default call should NOT fire the gate.
        # Lowering the threshold to 0.35 flips it.
        probs = {
            "catastrophizing": 0.10, "black_and_white": 0.06,
            "overgeneralization": 0.06, "mind_reading": 0.06,
            "fortune_telling": 0.06, "emotional_reasoning": 0.06,
            "should_statements": 0.05, "labeling": 0.05,
            "personalization": 0.05, "discounting_positive": 0.05,
            "none": 0.40,
        }
        # sums to 1.00 exactly; 'none' is argmax at 0.40
        assert abs(sum(probs.values()) - 1.0) < 1e-6
        r1 = select_multi_distortions(probs)  # default none_dominance=0.50
        assert r1.is_none is False
        r2 = select_multi_distortions(probs, none_dominance=0.35)
        assert r2.is_none is True


# ── threshold relaxation ───────────────────────────────────────────────
class TestThresholdRelax:
    def test_nothing_above_threshold_falls_back_to_min_count(self):
        probs = _dict_probs(
            catastrophizing=0.15, overgeneralization=0.12,
            mind_reading=0.10, none=0.35,
        )
        r = select_multi_distortions(probs, threshold=0.20, min_count=1)
        assert len(r.picks) == 1
        assert r.picks[0].distortion_type == "catastrophizing"
        assert "threshold_relaxed" in r.reason

    def test_min_count_zero_allows_empty_picks(self):
        # If no class is above the threshold AND min_count=0, we return
        # an empty pick list (rather than forcing a weak pick).
        probs = _dict_probs(catastrophizing=0.05, none=0.20)
        r = select_multi_distortions(probs, threshold=0.50, min_count=0, none_dominance=0.99)
        assert r.picks == []
        assert r.is_none is False  # none-gate didn't fire either
        assert "threshold_applied" in r.reason or "threshold_relaxed" in r.reason

    def test_custom_threshold_tightens_picks(self):
        probs = _dict_probs(
            catastrophizing=0.30, overgeneralization=0.25,
            mind_reading=0.15, none=0.10,
        )
        r = select_multi_distortions(probs, threshold=0.28)
        # Only catastrophizing is above 0.28
        assert len(r.picks) == 1
        assert r.picks[0].distortion_type == "catastrophizing"


# ── input normalisation ────────────────────────────────────────────────
class TestInputHandling:
    def test_accepts_sequence_with_class_names(self):
        probs_seq = [0.72] + [0.02] * 9 + [0.10]  # 11 entries
        r = select_multi_distortions(probs_seq, class_names=DISTORTION_CLASS_NAMES)
        assert r.picks[0].distortion_type == "catastrophizing"

    def test_sequence_without_class_names_raises(self):
        with pytest.raises(ValueError, match=r"class_names is required"):
            select_multi_distortions([0.5, 0.5])

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError, match=r"3 entries but class_names has 11"):
            select_multi_distortions([0.1, 0.2, 0.7], class_names=DISTORTION_CLASS_NAMES)

    def test_empty_probs_raises(self):
        with pytest.raises(ValueError, match=r"probs is empty"):
            select_multi_distortions({})

    def test_out_of_range_probability_raises(self):
        with pytest.raises(ValueError, match=r"out of \[0, 1\]"):
            select_multi_distortions({"catastrophizing": 1.5, "none": 0.0})

    def test_probabilities_must_sum_to_one(self):
        with pytest.raises(ValueError, match=r"sum to ~1.0"):
            select_multi_distortions({"catastrophizing": 0.3, "none": 0.3})

    def test_small_rounding_error_tolerated(self):
        # Sum = 1.01 — within the 0.05 tolerance.
        probs = _dict_probs(catastrophizing=0.5, none=0.45)
        assert abs(sum(probs.values()) - 1.0) < 0.05
        r = select_multi_distortions(probs)
        assert r.picks  # no ValueError


# ── parameter validation ───────────────────────────────────────────────
class TestParameterValidation:
    def test_invalid_threshold(self):
        with pytest.raises(ValueError, match=r"threshold must be in"):
            select_multi_distortions(_dict_probs(), threshold=1.5)

    def test_negative_min_count(self):
        with pytest.raises(ValueError, match=r"min_count must be >= 0"):
            select_multi_distortions(_dict_probs(), min_count=-1)

    def test_invalid_none_dominance(self):
        with pytest.raises(ValueError, match=r"none_dominance must be in"):
            select_multi_distortions(_dict_probs(), none_dominance=1.2)


# ── serialisation ──────────────────────────────────────────────────────
class TestSerialisation:
    def test_to_dict_shape(self):
        probs = _dict_probs(catastrophizing=0.40, overgeneralization=0.35, none=0.10)
        r = select_multi_distortions(probs)
        d = r.to_dict()
        assert set(d.keys()) == {
            "picks", "is_none", "primary", "co_occurrence_strength",
            "threshold_used", "reason", "all_probabilities", "count",
        }
        assert d["count"] == 2
        assert isinstance(d["picks"], list)
        assert d["picks"][0]["rank"] == 1
        assert "catastrophizing" in d["all_probabilities"]

    def test_pick_to_dict_rounds_confidence(self):
        p = DistortionPick(distortion_type="mind_reading", confidence=0.123456789, rank=1)
        d = p.to_dict()
        assert d["confidence"] == pytest.approx(0.1235, abs=1e-4)

    def test_to_dict_is_json_serialisable(self):
        import json
        probs = _dict_probs(catastrophizing=0.40, none=0.30)
        r = select_multi_distortions(probs)
        s = json.dumps(r.to_dict())
        assert '"catastrophizing"' in s


# ── classify_co_occurrence ─────────────────────────────────────────────
class TestClassifyCoOccurrence:
    def test_none_tag(self):
        probs = _dict_probs(none=0.80)
        r = select_multi_distortions(probs)
        assert classify_co_occurrence(r) == "none"

    def test_single_tag(self):
        probs = _dict_probs(catastrophizing=0.70, none=0.10)
        r = select_multi_distortions(probs)
        assert classify_co_occurrence(r) == "single"

    def test_pair_tag(self):
        probs = _dict_probs(catastrophizing=0.40, overgeneralization=0.35, none=0.05)
        r = select_multi_distortions(probs)
        assert classify_co_occurrence(r) == "pair"

    def test_cluster_tag(self):
        probs = _dict_probs(
            catastrophizing=0.22, overgeneralization=0.21,
            mind_reading=0.20, none=0.05,
        )
        r = select_multi_distortions(probs)
        assert classify_co_occurrence(r) == "cluster"


# ── module-level constants ─────────────────────────────────────────────
class TestConstants:
    def test_default_threshold_in_valid_range(self):
        assert 0.0 < DEFAULT_THRESHOLD < 1.0

    def test_default_caps_are_sensible(self):
        assert DEFAULT_MIN_DISTORTIONS >= 0
        assert DEFAULT_MAX_DISTORTIONS >= DEFAULT_MIN_DISTORTIONS
        # 3 is the clinically defensible ceiling; more than that crosses
        # into over-interpretation.
        assert DEFAULT_MAX_DISTORTIONS <= 5

    def test_none_class_present_in_class_list(self):
        assert NONE_CLASS_NAME in DISTORTION_CLASS_NAMES

    def test_none_dominance_is_majority(self):
        # Has to be at least 0.50 for the "dominance" phrasing to make sense
        assert NONE_DOMINANCE >= 0.50
