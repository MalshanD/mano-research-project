"""
Tests for ``lib.assesment.uncertainty`` — the Bayesian companion to the
Component 2 calibrator.

These tests are intentionally pure-numpy: they never touch tensorflow, so
they run on the same pytest harness as the rest of the suite. We use
callable fake predictors (``PredictFn`` implementations) to exercise the
MC-Dropout and input-perturbation samplers without needing a real Keras
model.
"""

from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np
import pytest

from lib.assesment import uncertainty as U
from lib.assesment.uncertainty import (
    CLASS_NAMES,
    DEFAULT_ENTROPY_CUTOFF,
    DEFAULT_STABILITY_CUTOFF,
    HEAD_NAMES,
    METHOD_DEGENERATE,
    METHOD_INPUT_PERTURBATION,
    METHOD_MC_DROPOUT,
    ClassStatistic,
    UncertaintyResult,
    aggregate_mc_samples,
    build_keras_predictors,
    entropy,
    input_perturbation_samples,
    is_degenerate,
    keras_has_dropout,
    mc_dropout_samples,
)


# ─────────────────────────── entropy() ──────────────────────────────────────


class TestEntropy:
    def test_uniform_3_classes_equals_ln3(self):
        uniform = np.array([1 / 3, 1 / 3, 1 / 3])
        assert entropy(uniform) == pytest.approx(math.log(3), rel=1e-6)

    def test_one_hot_is_zero(self):
        one_hot = np.array([1.0, 0.0, 0.0])
        assert entropy(one_hot) == pytest.approx(0.0, abs=1e-8)

    def test_batch_returns_mean(self):
        samples = np.array([
            [1.0, 0.0, 0.0],    # entropy 0
            [1 / 3, 1 / 3, 1 / 3],  # entropy ln(3)
        ])
        expected = (0.0 + math.log(3)) / 2
        assert entropy(samples) == pytest.approx(expected, rel=1e-6)

    def test_handles_zero_probabilities(self):
        # The _EPS clipping must prevent log(0) = -inf.
        probs = np.array([1.0, 0.0, 0.0])
        result = entropy(probs)
        assert math.isfinite(result)
        assert result >= 0

    def test_entropy_monotonic_with_spread(self):
        peaked = np.array([0.9, 0.05, 0.05])
        flat = np.array([0.4, 0.3, 0.3])
        assert entropy(flat) > entropy(peaked)


# ───────────────────────── aggregate_mc_samples() ──────────────────────────


class TestAggregateMcSamples:
    def test_invariant_samples_give_degenerate_signal(self):
        # Every MC sample is identical → no uncertainty information.
        sample = np.array([0.1, 0.2, 0.7])
        samples = np.tile(sample, (20, 1))
        result = aggregate_mc_samples("stress", samples, METHOD_MC_DROPOUT)

        assert result.head == "stress"
        assert result.method == METHOD_MC_DROPOUT
        assert result.n_samples == 20
        assert result.point_class == 2
        # With identical samples, MI = predictive - expected entropy ≈ 0.
        assert result.mutual_information == pytest.approx(0.0, abs=1e-6)
        # All argmaxes agree → stability 1.0 → reliable.
        assert result.prediction_stability == pytest.approx(1.0)
        assert result.is_reliable is True

    def test_highly_uncertain_samples_are_unreliable(self):
        # Uniform samples across 3 classes → max entropy, stability ~1/3.
        rng = np.random.default_rng(42)
        # Build samples whose argmax is split roughly evenly.
        raw = rng.dirichlet(alpha=[1, 1, 1], size=60)
        result = aggregate_mc_samples("anxiety", raw, METHOD_MC_DROPOUT)

        assert result.is_reliable is False
        assert result.prediction_stability < DEFAULT_STABILITY_CUTOFF

    def test_returns_per_class_statistics(self):
        samples = np.array([
            [0.2, 0.3, 0.5],
            [0.1, 0.4, 0.5],
            [0.3, 0.3, 0.4],
        ])
        result = aggregate_mc_samples("depression", samples, METHOD_MC_DROPOUT)

        assert len(result.class_statistics) == 3
        # Class 2 mean = (0.5 + 0.5 + 0.4) / 3 = 0.4667
        assert result.class_statistics[2].mean == pytest.approx(0.4667, abs=1e-3)
        assert result.class_statistics[2].min == pytest.approx(0.4)
        assert result.class_statistics[2].max == pytest.approx(0.5)

    def test_mutual_information_is_nonnegative(self):
        rng = np.random.default_rng(0)
        for _ in range(20):
            raw = rng.dirichlet(alpha=[0.5, 0.5, 0.5], size=15)
            result = aggregate_mc_samples("stress", raw, METHOD_MC_DROPOUT)
            assert result.mutual_information >= 0.0

    def test_uses_provided_point_probabilities(self):
        samples = np.array([
            [0.4, 0.4, 0.2],
            [0.5, 0.3, 0.2],
        ])
        explicit_point = [0.1, 0.1, 0.8]  # Point class is 2, but MC mean argmax is 0.
        result = aggregate_mc_samples(
            "stress", samples, METHOD_MC_DROPOUT,
            point_probabilities=explicit_point,
        )
        assert result.point_class == 2
        assert result.point_probabilities == [0.1, 0.1, 0.8]

    def test_rejects_non_2d_samples(self):
        with pytest.raises(ValueError, match="shape"):
            aggregate_mc_samples("stress", np.array([0.5, 0.5]), METHOD_MC_DROPOUT)

    def test_rejects_zero_samples(self):
        with pytest.raises(ValueError, match="at least one"):
            aggregate_mc_samples(
                "stress", np.empty((0, 3)), METHOD_MC_DROPOUT,
            )

    def test_rejects_mismatched_point_shape(self):
        samples = np.ones((5, 3)) / 3
        with pytest.raises(ValueError, match="shape"):
            aggregate_mc_samples(
                "stress", samples, METHOD_MC_DROPOUT,
                point_probabilities=[0.5, 0.5],  # wrong cardinality
            )

    def test_custom_class_names_shorter_than_classes_falls_back(self):
        samples = np.array([[0.25, 0.25, 0.25, 0.25]] * 5)
        result = aggregate_mc_samples(
            "stress", samples, METHOD_MC_DROPOUT,
            class_names=("A", "B"),  # shorter than num_classes=4
        )
        # Fallback class names "class2", "class3" used for c >= 2.
        names = [cs.class_name for cs in result.class_statistics]
        assert names[0] == "A"
        assert names[1] == "B"
        assert names[2] == "class2"
        assert names[3] == "class3"

    def test_summary_contains_head_and_percent(self):
        samples = np.tile(np.array([0.7, 0.2, 0.1]), (20, 1))
        result = aggregate_mc_samples("anxiety", samples, METHOD_MC_DROPOUT)
        assert "Anxiety" in result.summary
        assert "100%" in result.summary

    def test_unreliable_summary_flags_clinical_judgement(self):
        # Craft samples with argmaxes split 1/1/1 across 3 classes.
        samples = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
        ])
        # Point class is whichever mean-argmax wins a tie (class 0 here).
        result = aggregate_mc_samples("stress", samples, METHOD_MC_DROPOUT)
        # With 3 disjoint argmaxes and a tied mean, stability = 1/3.
        assert result.prediction_stability <= 0.34
        assert result.is_reliable is False


# ────────────────────────── is_degenerate() ────────────────────────────────


class TestIsDegenerate:
    def test_identical_samples_are_degenerate(self):
        samples = np.tile(np.array([0.1, 0.2, 0.7]), (10, 1))
        assert is_degenerate(samples) is True

    def test_single_sample_is_degenerate(self):
        assert is_degenerate(np.array([[0.3, 0.3, 0.4]])) is True

    def test_varying_samples_are_not_degenerate(self):
        samples = np.array([
            [0.1, 0.3, 0.6],
            [0.2, 0.3, 0.5],
            [0.1, 0.4, 0.5],
        ])
        assert is_degenerate(samples) is False

    def test_tiny_variation_within_tolerance(self):
        base = np.array([0.1, 0.2, 0.7])
        samples = np.tile(base, (5, 1))
        samples += 1e-9  # well inside the default atol=1e-6
        assert is_degenerate(samples) is True


# ───────────────────── input_perturbation_samples() ────────────────────────


def _make_fake_head_predictor(
    head_probs: Sequence[Sequence[float]],
) -> U.PredictFn:
    """A fake predict_fn that returns a fixed softmax per head regardless of input.

    Emulates Keras' multi-head output: a list of length ``n_heads`` where
    each entry is a ``(N, C)`` array. Used to test sampler plumbing without
    importing tensorflow.
    """
    def _predict(x: np.ndarray) -> List[np.ndarray]:
        n = x.shape[0]
        return [np.tile(np.asarray(p, dtype=float), (n, 1)) for p in head_probs]
    return _predict


class TestInputPerturbationSamples:
    def test_returns_one_array_per_head(self):
        predict = _make_fake_head_predictor([[0.5, 0.3, 0.2], [0.1, 0.8, 0.1]])
        row = np.ones(5)
        out = input_perturbation_samples(predict, row, n_samples=7, sigma=0.1)
        assert len(out) == 2
        for arr in out:
            assert arr.shape == (7, 3)

    def test_sigma_zero_gives_degenerate_samples(self):
        predict = _make_fake_head_predictor([[0.1, 0.2, 0.7]])
        row = np.ones(5)
        out = input_perturbation_samples(predict, row, n_samples=10, sigma=0.0)
        assert is_degenerate(out[0]) is True

    def test_accepts_row_shape_1xf(self):
        predict = _make_fake_head_predictor([[0.2, 0.3, 0.5]])
        row = np.ones((1, 4))
        out = input_perturbation_samples(predict, row, n_samples=3, sigma=0.05)
        assert out[0].shape == (3, 3)

    def test_rejects_bad_row_shape(self):
        predict = _make_fake_head_predictor([[0.2, 0.3, 0.5]])
        with pytest.raises(ValueError, match="shape"):
            input_perturbation_samples(predict, np.zeros((3, 4)), n_samples=5)

    def test_rejects_nonpositive_n_samples(self):
        predict = _make_fake_head_predictor([[0.2, 0.3, 0.5]])
        with pytest.raises(ValueError, match=">= 1"):
            input_perturbation_samples(predict, np.ones(5), n_samples=0)

    def test_deterministic_with_seeded_rng(self):
        # Use a predictor that passes through the perturbed input so the
        # samples vary with the random seed.
        def predict(x: np.ndarray) -> List[np.ndarray]:
            # Softmax-ish: just normalise per row after abs to keep it positive.
            pos = np.abs(x[:, :3])
            pos = pos / pos.sum(axis=1, keepdims=True)
            return [pos]

        row = np.array([1.0, 2.0, 3.0, 4.0])
        rng1 = np.random.default_rng(123)
        rng2 = np.random.default_rng(123)
        out1 = input_perturbation_samples(predict, row, n_samples=4, sigma=0.1, rng=rng1)
        out2 = input_perturbation_samples(predict, row, n_samples=4, sigma=0.1, rng=rng2)
        np.testing.assert_allclose(out1[0], out2[0])


# ───────────────────────── mc_dropout_samples() ────────────────────────────


class TestMcDropoutSamples:
    def test_calls_predictor_n_times(self):
        call_count = {"n": 0}

        def predict(x: np.ndarray) -> List[np.ndarray]:
            call_count["n"] += 1
            # Return different probs per call so samples truly vary.
            p = call_count["n"] / 100
            return [np.array([[p, 0.5 - p / 2, 0.5 - p / 2]])]

        row = np.ones(4)
        out = mc_dropout_samples(predict, row, n_samples=5)
        assert call_count["n"] == 5
        assert out[0].shape == (5, 3)

    def test_returns_one_matrix_per_head(self):
        def predict(x: np.ndarray) -> List[np.ndarray]:
            return [
                np.array([[0.2, 0.3, 0.5]]),
                np.array([[0.1, 0.1, 0.8]]),
                np.array([[0.4, 0.3, 0.3]]),
            ]

        out = mc_dropout_samples(predict, np.ones(4), n_samples=3)
        assert len(out) == 3
        for arr in out:
            assert arr.shape == (3, 3)

    def test_accepts_row_shape_f(self):
        def predict(x: np.ndarray) -> List[np.ndarray]:
            return [np.array([[0.25, 0.25, 0.25, 0.25]])]
        out = mc_dropout_samples(predict, np.ones(6), n_samples=2)
        assert out[0].shape == (2, 4)

    def test_rejects_bad_row_shape(self):
        def predict(x: np.ndarray) -> List[np.ndarray]:
            return [np.array([[0.5, 0.5]])]
        with pytest.raises(ValueError, match="shape"):
            mc_dropout_samples(predict, np.zeros((3, 4)), n_samples=5)

    def test_rejects_nonpositive_n_samples(self):
        def predict(x: np.ndarray) -> List[np.ndarray]:
            return [np.array([[0.5, 0.5]])]
        with pytest.raises(ValueError, match=">= 1"):
            mc_dropout_samples(predict, np.ones(4), n_samples=0)


# ─────────────────────────── keras_has_dropout() ───────────────────────────


class _FakeLayer:
    """Stand-in for a Keras layer — only class-name matters to the helper."""
    pass


class _FakeDropout:
    def __init__(self):
        # Mimic keras.layers.Dropout's class lookup.
        pass


_FakeDropout.__name__ = "Dropout"  # unittest-friendly metadata


class TestKerasHasDropout:
    def test_none_model_returns_false(self):
        assert keras_has_dropout(None) is False

    def test_model_without_dropout(self):
        class FakeModel:
            layers = [_FakeLayer(), _FakeLayer()]
        assert keras_has_dropout(FakeModel()) is False

    def test_model_with_dropout(self):
        class FakeModel:
            layers = [_FakeLayer(), _FakeDropout()]
        assert keras_has_dropout(FakeModel()) is True

    def test_nested_submodel_with_dropout(self):
        class SubModel:
            layers = [_FakeDropout()]

        class FakeModel:
            layers = [_FakeLayer(), SubModel()]
        assert keras_has_dropout(FakeModel()) is True

    def test_model_without_layers_attr(self):
        class BareModel:
            pass
        assert keras_has_dropout(BareModel()) is False


# ────────────────────────── build_keras_predictors ─────────────────────────


class TestBuildKerasPredictors:
    def test_deterministic_uses_training_false(self):
        captured = {"training": None}

        class FakeOutput:
            def __init__(self, arr):
                self._arr = arr
            def numpy(self):
                return self._arr

        class FakeModel:
            def __call__(self, x, training):
                captured["training"] = training
                return [FakeOutput(np.array([[0.1, 0.2, 0.7]]))]

        det, sto = build_keras_predictors(FakeModel())
        det(np.ones((1, 4)))
        assert captured["training"] is False

        sto(np.ones((1, 4)))
        assert captured["training"] is True

    def test_outputs_converted_to_numpy(self):
        class FakeOutput:
            def numpy(self):
                return np.array([[0.3, 0.3, 0.4]])

        class FakeModel:
            def __call__(self, x, training):
                return [FakeOutput()]

        det, _ = build_keras_predictors(FakeModel())
        out = det(np.ones((1, 4)))
        assert isinstance(out[0], np.ndarray)
        np.testing.assert_allclose(out[0], [[0.3, 0.3, 0.4]])


# ──────────────────────── UncertaintyResult.to_dict ────────────────────────


class TestUncertaintyResultSerialisation:
    def test_to_dict_contains_all_fields(self):
        samples = np.tile(np.array([0.1, 0.2, 0.7]), (4, 1))
        result = aggregate_mc_samples("stress", samples, METHOD_MC_DROPOUT)
        payload = result.to_dict()
        for key in (
            "head", "method", "n_samples",
            "point_probabilities", "point_class",
            "mean_probabilities", "class_statistics",
            "predictive_entropy", "expected_entropy",
            "mutual_information", "prediction_stability",
            "is_reliable", "summary",
        ):
            assert key in payload, f"Missing key: {key}"

    def test_class_statistics_are_plain_dicts(self):
        samples = np.tile(np.array([0.1, 0.2, 0.7]), (4, 1))
        result = aggregate_mc_samples("stress", samples, METHOD_MC_DROPOUT)
        payload = result.to_dict()
        for cs in payload["class_statistics"]:
            assert isinstance(cs, dict)
            assert "class_index" in cs and "class_name" in cs

    def test_round_trip_json_serialisable(self):
        import json
        samples = np.tile(np.array([0.1, 0.2, 0.7]), (4, 1))
        result = aggregate_mc_samples("anxiety", samples, METHOD_INPUT_PERTURBATION)
        # Raises TypeError if anything is still a numpy scalar.
        json_str = json.dumps(result.to_dict())
        loaded = json.loads(json_str)
        assert loaded["head"] == "anxiety"
        assert loaded["method"] == METHOD_INPUT_PERTURBATION


# ──────────────────────── module-level constants sanity ────────────────────


def test_method_constants_are_distinct():
    assert len({METHOD_MC_DROPOUT, METHOD_INPUT_PERTURBATION, METHOD_DEGENERATE}) == 3


def test_head_names_match_three_heads():
    assert HEAD_NAMES == ("stress", "anxiety", "depression")


def test_class_names_match_three_levels():
    assert CLASS_NAMES == ("Low", "Moderate", "High")


def test_reliability_cutoffs_sensible():
    # These drive the clinical "reliable" flag — if they change, update
    # Component 1's thresholds and the dashboard copy to match.
    assert 0.0 < DEFAULT_STABILITY_CUTOFF < 1.0
    assert DEFAULT_ENTROPY_CUTOFF > 0.0
