"""
Tests for lib/activity/feed_explainer.py
=========================================
Covers permutation-based per-feature attribution for the Feed Ranker.

Most tests are torch-free — they use a mock model + mock scaler to
verify the attribution math, group layout, sorting, and top-k clipping.
A small number of integration tests skip when torch isn't installed.
"""
from __future__ import annotations

import numpy as np
import pytest

from lib.CBT.feed_explainer import (
    FEATURE_GROUPS,
    GROUP_LABELS,
    GroupAttribution,
    explain_prediction,
    explain_predictions_batch,
    is_available,
)

try:
    import torch
    import torch.nn  # noqa: F401 -- mirrors feed_explainer; partial stubs fail here
    TORCH_AVAILABLE = True
except (ImportError, AttributeError):
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants & schema
# ---------------------------------------------------------------------------

class TestFeatureGroups:
    def test_groups_cover_all_23_features(self):
        # Slices must cover [0, 23) without gaps or overlaps.
        covered = set()
        for name, start, end, baseline in FEATURE_GROUPS:
            for i in range(start, end):
                assert i not in covered, f"feature {i} covered twice"
                covered.add(i)
            assert baseline.shape == (end - start,)
        assert covered == set(range(23))

    def test_group_labels_present(self):
        for name, _, _, _ in FEATURE_GROUPS:
            assert name in GROUP_LABELS
            assert isinstance(GROUP_LABELS[name], str)
            assert len(GROUP_LABELS[name]) > 0


class TestGroupAttribution:
    def test_to_dict_roundtrip(self):
        a = GroupAttribution("user_profile", "Matches your profile", 0.123, 0.123)
        d = a.to_dict()
        assert d["group"] == "user_profile"
        assert d["label"] == "Matches your profile"
        assert d["delta"] == 0.123
        assert d["abs_delta"] == 0.123

    def test_dict_rounds_to_4_dp(self):
        a = GroupAttribution("x", "X", 0.123456789, 0.123456789)
        d = a.to_dict()
        assert d["delta"] == 0.1235  # rounded
        assert d["abs_delta"] == 0.1235


# ---------------------------------------------------------------------------
# Mock-model attribution math (no torch required)
# ---------------------------------------------------------------------------

class _IdentityScaler:
    """Mimic an sklearn StandardScaler that's a no-op."""
    def transform(self, X):
        return np.asarray(X, dtype=np.float32)


class _MockModel:
    """Linear MLP-look-alike: score = sigmoid(weights · x).

    Constructed so we can predict per-group ablation deltas exactly.
    Wraps in a torch-tensor-compatible interface only when torch is
    available; for non-torch tests we operate on numpy.
    """

    def __init__(self, weights):
        self.weights = np.asarray(weights, dtype=np.float32)

    def __call__(self, X):
        # X is either a torch.FloatTensor or numpy
        if TORCH_AVAILABLE and isinstance(X, torch.Tensor):
            arr = X.cpu().numpy()
        else:
            arr = np.asarray(X)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        z = arr @ self.weights
        # mimic sigmoid output
        out = 1.0 / (1.0 + np.exp(-z))
        if TORCH_AVAILABLE:
            return torch.FloatTensor(out)
        return out

    def eval(self):
        return self


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
class TestExplainPrediction:
    def setup_method(self):
        # Heavily weight the user_profile group so its ablation drops
        # the score the most. Other groups ~ neutral.
        weights = np.zeros(23, dtype=np.float32)
        weights[0:7] = 1.0   # user_profile
        weights[7:12] = 0.1  # post_type
        weights[12:22] = 0.1  # text_content
        weights[22] = 0.1     # recency
        self.model = _MockModel(weights)
        self.scaler = _IdentityScaler()

    def test_returns_correct_shape(self):
        feats = np.ones(23, dtype=np.float32) * 0.5
        result = explain_prediction(self.model, self.scaler, feats, top_k=None)
        assert len(result) == len(FEATURE_GROUPS)
        for r in result:
            assert isinstance(r, GroupAttribution)

    def test_user_profile_dominates_when_weighted_high(self):
        feats = np.ones(23, dtype=np.float32)
        result = explain_prediction(self.model, self.scaler, feats, top_k=None)
        # Heaviest weight on user_profile → highest abs_delta.
        groups_sorted = [r.group for r in result]
        assert groups_sorted[0] == "user_profile"

    def test_top_k_clips_results(self):
        feats = np.ones(23, dtype=np.float32)
        result = explain_prediction(self.model, self.scaler, feats, top_k=2)
        assert len(result) == 2

    def test_invalid_shape_returns_empty(self):
        feats = np.ones(10, dtype=np.float32)  # wrong size
        result = explain_prediction(self.model, self.scaler, feats)
        assert result == []

    def test_delta_uses_provided_base_score(self):
        feats = np.ones(23, dtype=np.float32)
        # Pre-pass a manufactured score; delta should be measured
        # against THIS, not a fresh forward pass.
        result = explain_prediction(
            self.model, self.scaler, feats,
            base_score=0.99, top_k=None,
        )
        # All deltas should be ≥ 0 because ablating any group can only
        # subtract from the score (the model's output is always in [0,1]
        # and base_score=0.99 is near max).
        for r in result:
            # All groups have positive weight → ablation drops score
            assert r.delta > 0


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
class TestExplainBatch:
    def setup_method(self):
        weights = np.zeros(23, dtype=np.float32)
        weights[0:7] = 1.0
        weights[7:12] = 0.1
        weights[12:22] = 0.1
        weights[22] = 0.1
        self.model = _MockModel(weights)
        self.scaler = _IdentityScaler()

    def test_batch_returns_list_of_lists(self):
        feats = np.ones((3, 23), dtype=np.float32)
        base = np.array([0.9, 0.8, 0.7], dtype=np.float32)
        result = explain_predictions_batch(
            self.model, self.scaler, feats, base, top_k=2
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 2
            for r in row:
                assert isinstance(r, GroupAttribution)

    def test_batch_invalid_shape_returns_empty_per_row(self):
        feats = np.ones((3, 10), dtype=np.float32)  # wrong shape
        base = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        result = explain_predictions_batch(
            self.model, self.scaler, feats, base
        )
        assert result == [[], [], []]


# ---------------------------------------------------------------------------
# Torch-free smoke tests
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_is_available_matches_torch_import(self):
        assert is_available() is TORCH_AVAILABLE


class TestNonTorchPath:
    def test_explain_prediction_no_torch_returns_empty(self):
        if TORCH_AVAILABLE:
            pytest.skip("torch is available; this branch is torch-absent only")
        feats = np.ones(23, dtype=np.float32)
        result = explain_prediction(None, None, feats)
        assert result == []

    def test_batch_no_torch_returns_empty_lists(self):
        if TORCH_AVAILABLE:
            pytest.skip("torch is available; this branch is torch-absent only")
        feats = np.ones((2, 23), dtype=np.float32)
        base = np.array([0.5, 0.5], dtype=np.float32)
        result = explain_predictions_batch(None, None, feats, base)
        assert result == [[], []]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
