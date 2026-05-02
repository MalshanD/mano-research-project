"""
Unit tests for ``lib.activity.activity_uncertainty``.

Uses a pure-numpy sample stack where possible so the tests pass even
without torch installed. The torch-dependent tests are skipped if
torch is unavailable.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from lib.activity.activity_uncertainty import (
    DEFAULT_N_SAMPLES,
    HIGH_UNCERTAINTY_CV_THRESHOLD,
    TORCH_AVAILABLE,
    UncertaintyEstimate,
    _safe_cv,
    predict_with_uncertainty,
    summarise_numpy_samples,
    summarise_predictions,
)


# ── Summary math ─────────────────────────────────────────────────────

class TestSummarisePredictions:
    def test_single_batch_shape(self):
        samples = np.array([[0.5], [0.6], [0.55], [0.58], [0.52]])
        out = summarise_predictions(samples)
        assert len(out) == 1
        est = out[0]
        assert isinstance(est, UncertaintyEstimate)
        assert est.n_samples == 5
        assert abs(est.mean - 0.55) < 1e-3

    def test_multi_batch_shape(self):
        # 4 MC samples over 3 items
        samples = np.array([
            [0.1, 0.5, 0.9],
            [0.12, 0.48, 0.92],
            [0.11, 0.52, 0.88],
            [0.09, 0.49, 0.91],
        ])
        out = summarise_predictions(samples)
        assert len(out) == 3
        # Low-variance items should have small std
        assert out[0].std < 0.05
        assert out[1].std < 0.05

    def test_1d_input_treated_as_single_item_batch(self):
        samples = np.array([0.5, 0.6, 0.55])
        out = summarise_predictions(samples)
        assert len(out) == 1

    def test_invalid_3d_raises(self):
        bad = np.zeros((2, 3, 4))
        with pytest.raises(ValueError, match="must be"):
            summarise_predictions(bad)

    def test_n_samples_1_gives_zero_std(self):
        # A single sample can't give a meaningful std — we return 0 instead of NaN.
        out = summarise_predictions(np.array([[0.5, 0.7]]))
        assert out[0].std == 0.0
        assert out[1].std == 0.0

    def test_ci_bounds(self):
        # With samples spanning 0.1 to 0.9, CI should be within bounds.
        samples = np.linspace(0.1, 0.9, 100).reshape(-1, 1)
        out = summarise_predictions(samples)[0]
        assert out.ci_low >= 0.1
        assert out.ci_high <= 0.9
        assert out.ci_low < out.mean < out.ci_high


# ── UncertaintyEstimate dataclass ────────────────────────────────────

class TestUncertaintyEstimate:
    def test_to_dict_shape(self):
        est = UncertaintyEstimate(
            mean=0.5, std=0.05, ci_low=0.4, ci_high=0.6,
            cv=0.1, n_samples=20,
        )
        d = est.to_dict()
        required = {"mean", "std", "ci_low", "ci_high", "cv",
                    "n_samples", "is_high_uncertainty"}
        assert required <= set(d.keys())
        assert d["is_high_uncertainty"] is False

    def test_high_uncertainty_flag_triggers(self):
        est = UncertaintyEstimate(
            mean=0.5, std=0.25, ci_low=0.1, ci_high=0.9,
            cv=0.5, n_samples=20,
        )
        assert est.is_high_uncertainty is True
        assert est.to_dict()["is_high_uncertainty"] is True

    def test_cv_exactly_at_threshold(self):
        # CV exactly at the threshold counts as high-uncertainty (>=).
        est = UncertaintyEstimate(
            mean=1.0, std=HIGH_UNCERTAINTY_CV_THRESHOLD,
            ci_low=0.0, ci_high=2.0,
            cv=HIGH_UNCERTAINTY_CV_THRESHOLD, n_samples=20,
        )
        assert est.is_high_uncertainty is True


# ── CV safety ────────────────────────────────────────────────────────

class TestSafeCV:
    def test_cv_normal(self):
        mean = np.array([0.5])
        std = np.array([0.1])
        assert _safe_cv(mean, std)[0] == 0.2

    def test_cv_zero_mean_does_not_divide_by_zero(self):
        mean = np.array([0.0])
        std = np.array([0.1])
        out = _safe_cv(mean, std)
        # Should not be NaN or inf
        assert math.isfinite(out[0])

    def test_cv_negative_mean_uses_absolute(self):
        mean = np.array([-0.5])
        std = np.array([0.1])
        assert _safe_cv(mean, std)[0] == 0.2


# ── numpy convenience entrypoint ─────────────────────────────────────

class TestSummariseNumpySamples:
    def test_passes_through_to_summariser(self):
        samples = [[0.1, 0.5], [0.2, 0.6]]
        out = summarise_numpy_samples(samples)
        assert len(out) == 2

    def test_accepts_python_list(self):
        out = summarise_numpy_samples([[0.5], [0.55], [0.6]])
        assert len(out) == 1
        assert abs(out[0].mean - 0.55) < 1e-3


# ── Torch-dependent tests ────────────────────────────────────────────

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
class TestTorchPath:
    def _make_dropout_net(self, p: float = 0.5):
        import torch.nn as nn
        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(4, 8), nn.ReLU(), nn.Dropout(p),
                    nn.Linear(8, 1), nn.Sigmoid(),
                )
            def forward(self, x):
                return self.net(x).squeeze(-1)
        return Net()

    def test_mc_dropout_gives_nonzero_variance(self):
        import torch
        torch.manual_seed(0)
        model = self._make_dropout_net(p=0.5)
        X = torch.randn(3, 4)
        ests = predict_with_uncertainty(model, X, n_samples=30)
        assert len(ests) == 3
        # With p=0.5, stds should be non-trivial (>0.01).
        for e in ests:
            assert e.std > 0.001

    def test_model_restored_to_eval_after_forward(self):
        import torch
        model = self._make_dropout_net(p=0.3)
        X = torch.randn(2, 4)
        predict_with_uncertainty(model, X, n_samples=10)
        # After the forward sweep, the whole model should be in eval mode.
        assert not model.training
        # Drop-specific check: dropout modules should also be back to eval.
        for mod in model.modules():
            if isinstance(mod, torch.nn.Dropout):
                assert not mod.training, "dropout left in train mode after sweep"

    def test_n_samples_zero_raises(self):
        model = self._make_dropout_net()
        import torch
        with pytest.raises(ValueError, match="n_samples"):
            predict_with_uncertainty(model, torch.randn(1, 4), n_samples=0)

    def test_no_dropout_warns_but_runs(self, caplog):
        import logging
        import torch.nn as nn
        import torch
        class NoDropout(nn.Module):
            def __init__(self):
                super().__init__()
                self.lin = nn.Linear(4, 1)
            def forward(self, x):
                return self.lin(x).squeeze(-1)

        model = NoDropout()
        with caplog.at_level(logging.WARNING, logger="component4.activity_uncertainty"):
            ests = predict_with_uncertainty(model, torch.randn(2, 4), n_samples=5)
        # The sweep still runs; warning is advisory.
        assert len(ests) == 2
        assert any("no Dropout layers" in r.message for r in caplog.records)

    def test_1d_input_promoted(self):
        import torch
        model = self._make_dropout_net()
        X = torch.randn(4)  # 1-D, should be treated as batch of 1
        ests = predict_with_uncertainty(model, X, n_samples=5)
        assert len(ests) == 1


# ── Constants sanity ─────────────────────────────────────────────────

class TestConstants:
    def test_default_n_samples_reasonable(self):
        assert 10 <= DEFAULT_N_SAMPLES <= 100

    def test_high_uncertainty_threshold_reasonable(self):
        assert 0.1 < HIGH_UNCERTAINTY_CV_THRESHOLD < 1.0
