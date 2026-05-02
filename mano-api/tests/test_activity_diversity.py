"""
Tests for lib/activity/activity_diversity.py
=============================================
Covers cold-start detection & default filling, and the MMR diversity
re-ranker. Pure-Python — no torch / DB dependencies.
"""
from __future__ import annotations

import pytest

from lib.activity.activity_diversity import (
    COLD_START_PROFILE,
    apply_cold_start_defaults,
    is_cold_start,
    mmr_rerank,
    prepare_user_scores,
)


# ---------------------------------------------------------------------------
# Cold-start detection
# ---------------------------------------------------------------------------
class TestIsColdStart:
    def test_empty_dict_is_cold(self):
        assert is_cold_start({}) is True

    def test_none_input_is_cold(self):
        # prepare_user_scores handles None, but is_cold_start should be
        # defensive too — an empty-or-None profile is cold.
        assert is_cold_start({}) is True

    def test_all_none_is_cold(self):
        profile = {k: None for k in COLD_START_PROFILE}
        assert is_cold_start(profile) is True

    def test_all_zero_is_cold(self):
        profile = {k: 0 for k in COLD_START_PROFILE}
        assert is_cold_start(profile) is True

    def test_all_sub_threshold_is_cold(self):
        profile = {k: 2.0 for k in COLD_START_PROFILE}  # below 5.0 threshold
        assert is_cold_start(profile) is True

    def test_one_meaningful_score_is_not_cold(self):
        profile = {k: 0 for k in COLD_START_PROFILE}
        profile["stress_score"] = 80
        assert is_cold_start(profile) is False

    def test_non_numeric_ignored(self):
        profile = {k: "bad" for k in COLD_START_PROFILE}
        assert is_cold_start(profile) is True

    def test_partial_profile_with_signal(self):
        # Only two dims present, both high — NOT cold
        profile = {"stress_score": 70, "anxiety_score": 60}
        assert is_cold_start(profile) is False


class TestApplyColdStartDefaults:
    def test_empty_returns_full_prior(self):
        result = apply_cold_start_defaults({})
        for k, v in COLD_START_PROFILE.items():
            assert result[k] == v

    def test_none_returns_full_prior(self):
        result = apply_cold_start_defaults(None)
        assert result == COLD_START_PROFILE

    def test_real_value_preserved(self):
        profile = {"stress_score": 80, "anxiety_score": None}
        result = apply_cold_start_defaults(profile)
        assert result["stress_score"] == 80
        assert result["anxiety_score"] == COLD_START_PROFILE["anxiety_score"]

    def test_invalid_type_replaced(self):
        profile = {"stress_score": "garbage"}
        result = apply_cold_start_defaults(profile)
        assert result["stress_score"] == COLD_START_PROFILE["stress_score"]

    def test_zero_is_kept(self):
        # Filling only replaces None/invalid; a legitimate 0 is preserved.
        profile = {"stress_score": 0}
        result = apply_cold_start_defaults(profile)
        assert result["stress_score"] == 0
        assert result["anxiety_score"] == COLD_START_PROFILE["anxiety_score"]

    def test_does_not_mutate_input(self):
        profile = {"stress_score": 70}
        snapshot = dict(profile)
        apply_cold_start_defaults(profile)
        assert profile == snapshot


class TestPrepareUserScores:
    def test_flag_off_passes_through(self):
        profile = {"stress_score": 10}
        scores, cold = prepare_user_scores(profile, with_cold_start_fallback=False)
        assert scores == profile
        assert cold is False

    def test_cold_profile_is_detected_and_filled(self):
        scores, cold = prepare_user_scores({}, with_cold_start_fallback=True)
        assert cold is True
        assert scores == COLD_START_PROFILE

    def test_real_profile_keeps_values(self):
        profile = {"stress_score": 80, "anxiety_score": 70}
        scores, cold = prepare_user_scores(profile, with_cold_start_fallback=True)
        assert cold is False
        assert scores["stress_score"] == 80
        # Missing dims are filled
        assert scores["depression_score"] == COLD_START_PROFILE["depression_score"]

    def test_none_input(self):
        scores, cold = prepare_user_scores(None, with_cold_start_fallback=True)
        assert cold is True
        assert scores == COLD_START_PROFILE


# ---------------------------------------------------------------------------
# MMR diversity re-ranking
# ---------------------------------------------------------------------------
def _make_result(act_id, category, relevance, conditions=None, problems=None):
    return {
        "activity": {
            "id": act_id,
            "category": category,
            "target_conditions": conditions or [],
            "target_problems": problems or [],
        },
        "relevance_score": relevance,
    }


class TestMmrRerank:
    def test_empty_input(self):
        assert mmr_rerank([]) == []

    def test_single_item_passthrough(self):
        items = [_make_result("a", "stress_relief", 90)]
        assert mmr_rerank(items) == items

    def test_lambda_1_is_identity(self):
        # λ=1.0 → pure relevance → order unchanged.
        items = [
            _make_result("a", "mindfulness", 90),
            _make_result("b", "mindfulness", 85),
            _make_result("c", "physical", 80),
        ]
        result = mmr_rerank(items, lambda_diversity=1.0)
        assert [r["activity"]["id"] for r in result] == ["a", "b", "c"]

    def test_lambda_low_promotes_different_category(self):
        # Top-by-relevance is two mindfulness items then a physical one.
        # With heavy diversity, the physical item should jump ahead of
        # the second mindfulness item.
        items = [
            _make_result("m1", "mindfulness", 95),
            _make_result("m2", "mindfulness", 90),
            _make_result("p1", "physical", 80),
        ]
        result = mmr_rerank(items, lambda_diversity=0.3, top_k=3)
        ids = [r["activity"]["id"] for r in result]
        assert ids[0] == "m1"  # highest relevance always first
        assert ids[1] == "p1"  # diversity promotes different category
        assert ids[2] == "m2"

    def test_annotates_mmr_score(self):
        items = [
            _make_result("a", "stress_relief", 90),
            _make_result("b", "physical", 80),
        ]
        result = mmr_rerank(items, lambda_diversity=0.5)
        for r in result:
            assert "mmr_score" in r
            assert isinstance(r["mmr_score"], float)

    def test_top_k_bounds_reranking(self):
        # Items past top_k should keep their original order even if
        # they'd be interesting for diversity.
        items = [
            _make_result("m1", "mindfulness", 95),
            _make_result("m2", "mindfulness", 90),
            _make_result("p1", "physical", 10),  # way down the list
        ]
        result = mmr_rerank(items, lambda_diversity=0.3, top_k=2)
        # Only first two get re-ranked — position 2 stays untouched.
        assert result[2]["activity"]["id"] == "p1"

    def test_similar_tags_lower_ranking(self):
        # Same category + same conditions = high similarity → penalised.
        items = [
            _make_result("a", "stress_relief", 95, conditions=["stress"]),
            _make_result("b", "stress_relief", 94, conditions=["stress"]),
            _make_result("c", "social", 90, conditions=["loneliness"]),
        ]
        result = mmr_rerank(items, lambda_diversity=0.3)
        ids = [r["activity"]["id"] for r in result]
        # "c" should appear before "b" because it's different on both
        # category and conditions.
        assert ids[0] == "a"
        assert ids.index("c") < ids.index("b")

    def test_does_not_lose_items(self):
        items = [_make_result(f"x{i}", "mindfulness", 100 - i) for i in range(10)]
        result = mmr_rerank(items, lambda_diversity=0.5, top_k=5)
        assert len(result) == 10
        assert {r["activity"]["id"] for r in result} == {r["activity"]["id"] for r in items}

    def test_all_zero_relevance(self):
        # No divide-by-zero blow-up when every item scores 0.
        items = [
            _make_result("a", "mindfulness", 0),
            _make_result("b", "physical", 0),
        ]
        result = mmr_rerank(items, lambda_diversity=0.5)
        assert len(result) == 2

    def test_lambda_above_one_clamps(self):
        items = [_make_result("a", "x", 10), _make_result("b", "y", 5)]
        # Explicit identity when lambda >= 1
        result = mmr_rerank(items, lambda_diversity=1.5)
        assert [r["activity"]["id"] for r in result] == ["a", "b"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
