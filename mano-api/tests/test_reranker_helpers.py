"""
PPO Reranker — pure-function tests.

We can't run the full ``rerank()`` without loading the frozen PPO agent +
Seq2Seq simulator (torch, .pth files, CUDA). These tests lock down the
side-effect-free helpers: weight normalisation, axis score derivation,
explanation ranking, and contraindication safety blocks.
"""

from __future__ import annotations

import pytest

from lib.synthetic.reranker_service import (
    _adherence_score,
    _care_phase_score,
    _explanation,
    _normalise_risk_reduction,
    _preference_score,
    _safety_blocks,
    _validate_weights,
    INTERVENTION_SLUGS,
)
from schemas.synthetic.reranker_schema import (
    AdherencePrior,
    PatientPreferences,
    RerankerWeights,
)


class TestValidateWeights:
    def test_default_weights_sum_to_one(self):
        w = _validate_weights(RerankerWeights())
        total = (
            w.w_ppo_policy + w.w_simulator_risk_reduction + w.w_adherence_prior
            + w.w_care_phase_prior + w.w_patient_preference
        )
        assert abs(total - 1.0) < 1e-9

    def test_relative_weights_get_normalised(self):
        raw = RerankerWeights(
            w_ppo_policy=2, w_simulator_risk_reduction=4,
            w_adherence_prior=2, w_care_phase_prior=1, w_patient_preference=1,
        )
        # Totals to 10 — should normalise to the ratios above.
        w = _validate_weights(raw)
        assert w.w_ppo_policy == pytest.approx(0.2)
        assert w.w_simulator_risk_reduction == pytest.approx(0.4)

    def test_all_zero_weights_raises(self):
        with pytest.raises(ValueError):
            _validate_weights(RerankerWeights(
                w_ppo_policy=0, w_simulator_risk_reduction=0,
                w_adherence_prior=0, w_care_phase_prior=0, w_patient_preference=0,
            ))


class TestNormaliseRiskReduction:
    def test_clamps_to_unit_interval(self):
        assert _normalise_risk_reduction(-1.0) == pytest.approx(0.0)
        assert _normalise_risk_reduction(1.0) == pytest.approx(1.0)

    def test_zero_is_mid_range(self):
        assert _normalise_risk_reduction(0.0) == pytest.approx(0.5)

    def test_monotonic(self):
        vals = [-0.3, -0.1, 0.0, 0.1, 0.3]
        normed = [_normalise_risk_reduction(v) for v in vals]
        assert normed == sorted(normed)


class TestAxisScoreHelpers:
    def test_adherence_defaults_to_neutral_when_absent(self):
        assert _adherence_score(None, "cbt") == 0.5

    def test_adherence_returns_value_when_present(self):
        prior = AdherencePrior(cbt=0.9)
        assert _adherence_score(prior, "cbt") == 0.9
        # Missing field falls back to neutral
        assert _adherence_score(prior, "exercise") == 0.5

    def test_preference_uses_same_convention(self):
        prefs = PatientPreferences(exercise=0.1)
        assert _preference_score(prefs, "exercise") == 0.1
        assert _preference_score(None, "exercise") == 0.5

    def test_care_phase_prior_reflects_table(self):
        # Intake should weight control high and medication low.
        assert _care_phase_score("intake", "control") > _care_phase_score("intake", "medication")
        # Practice phase should favour CBT / exercise.
        assert _care_phase_score("practice", "cbt") > _care_phase_score("practice", "medication")


class TestSafetyBlocks:
    def test_intake_always_blocks_medication(self):
        blocks = _safety_blocks(contraindications=[], care_phase="intake")
        assert "medication" in blocks

    def test_non_intake_respects_caller_list_only(self):
        blocks = _safety_blocks(contraindications=["cbt"], care_phase="practice")
        assert blocks == ["cbt"]

    def test_duplicates_collapsed(self):
        blocks = _safety_blocks(
            contraindications=["medication", "medication"], care_phase="intake",
        )
        assert blocks.count("medication") == 1


class TestExplanation:
    def test_picks_top_three_contributors(self):
        weights = RerankerWeights(
            w_ppo_policy=0.1, w_simulator_risk_reduction=0.4,
            w_adherence_prior=0.3, w_care_phase_prior=0.1,
            w_patient_preference=0.1,
        )
        scores = {
            "ppo_policy_score": 0.2,
            "simulator_risk_reduction_score": 0.9,  # top by a mile (weight × score)
            "adherence_prior_score": 0.8,
            "care_phase_prior_score": 0.2,
            "patient_preference_score": 0.2,
        }
        sentence, factors = _explanation(weights, "cbt", scores, "CBT")
        assert "CBT" in sentence
        assert "simulator risk reduction" in factors[0]
        assert len(factors) == 3


class TestInterventionVocab:
    def test_slug_ordering_matches_canonical_action_ids(self):
        # This ordering is load-bearing: reranker uses index-in-slug-list as the
        # action id fed to the PPO agent. A refactor that accidentally reorders
        # this list would silently corrupt every recommendation, so lock it in.
        assert INTERVENTION_SLUGS == [
            "control", "wellness_app", "cbt", "exercise", "medication",
        ]
