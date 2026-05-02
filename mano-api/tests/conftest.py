"""
Shared pytest fixtures.

These tests intentionally avoid loading the frozen ML models (CTGAN
pickle, TimeGAN .pth, PPO / Seq2Seq / LSTM .pth) — the sandbox has neither
torch nor the 1-2GB of model artefacts. We stub ``torch`` and the
intervention/risk services at import time so the service modules can be
imported and exercised on pure-Python CI runners as well as GPU boxes.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest


# ─── Path setup ──────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─── Stub torch + ml_models before any synthetic service imports ────────

def _install_torch_stub() -> None:
    if "torch" in sys.modules:
        return
    torch_stub = types.ModuleType("torch")
    torch_stub.cuda = types.SimpleNamespace(
        is_available=lambda: False,
        device_count=lambda: 0,
        manual_seed_all=lambda *a, **k: None,
    )
    torch_stub.manual_seed = lambda *a, **k: None
    torch_stub.FloatTensor = lambda *a, **k: None
    torch_stub.no_grad = lambda: (lambda f=None: f)
    torch_stub.load = lambda *a, **k: {}
    torch_stub.softmax = lambda *a, **k: None
    sys.modules["torch"] = torch_stub


def _install_ml_model_stubs() -> None:
    parent = types.ModuleType("ml_models")
    parent.__path__ = []
    component1 = types.ModuleType("ml_models.component1")
    component1.__path__ = []
    sys.modules["ml_models"] = parent
    sys.modules["ml_models.component1"] = component1

    tg_def = types.ModuleType("ml_models.component1.timegan_model_Def")
    tg_def.TimeGAN = object
    tg_def.TIMEGAN_DEFAULTS = {"seq_len": 7, "n_signals": 4, "hidden_dim": 24, "num_layers": 3}
    tg_def.SIGNAL_NAMES = ["Sleep Duration", "Quality of Sleep", "Heart Rate", "Stress Level"]
    sys.modules["ml_models.component1.timegan_model_Def"] = tg_def

    seq2seq = types.ModuleType("ml_models.component1.seq2seq_model_Def")
    seq2seq.InterventionSimulator = object
    sys.modules["ml_models.component1.seq2seq_model_Def"] = seq2seq

    sim_cfg = types.ModuleType("ml_models.component1.sim_config")
    sim_cfg.SimConfig = type("SimConfig", (), {})
    sys.modules["ml_models.component1.sim_config"] = sim_cfg

    rl = types.ModuleType("ml_models.component1.rl_agent_Def")
    rl.ActorCritic = object
    sys.modules["ml_models.component1.rl_agent_Def"] = rl

    lstm = types.ModuleType("ml_models.component1.lstm_model_Def")
    lstm.RiskPredictionModel = object
    sys.modules["ml_models.component1.lstm_model_Def"] = lstm

    lstm_cfg = types.ModuleType("ml_models.component1.lstm_config")
    lstm_cfg.LSTMConfig = type("LSTMConfig", (), {})
    sys.modules["ml_models.component1.lstm_config"] = lstm_cfg


_install_torch_stub()
_install_ml_model_stubs()


@pytest.fixture
def passport_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "passports"
    d.mkdir()
    monkeypatch.setenv("MANO_PASSPORT_DIR", str(d))
    return d


@pytest.fixture
def research_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "research_cohorts"
    d.mkdir()
    monkeypatch.setenv("MANO_RESEARCH_DIR", str(d))
    return d


@pytest.fixture
def fake_generators(monkeypatch):
    import numpy as np
    import pandas as pd

    class _FakeCTGAN:
        def is_loaded(self) -> bool: return True
        def generate(self, num_samples: int) -> pd.DataFrame:
            rng = np.random.default_rng(0)
            return pd.DataFrame({
                "Age": rng.integers(22, 60, size=num_samples),
                "Gender": rng.choice(["Male", "Female", "Other"], size=num_samples),
                "Country": rng.choice(["USA", "UK", "Sri Lanka", "India"], size=num_samples),
                "treatment": rng.choice(["Yes", "No"], size=num_samples),
                "work_interfere": rng.choice(["Never", "Sometimes", "Often"], size=num_samples),
            })

    class _FakeTimeGAN:
        def is_loaded(self) -> bool: return True
        def generate_denormalized(self, num_samples: int):
            rng = np.random.default_rng(1)
            return rng.uniform(
                low=[4.0, 0.2, 60, 0.1],
                high=[9.0, 0.9, 95, 0.9],
                size=(num_samples, 7, 4),
            )

    from lib.synthetic import ctgan_service, timegan_service
    monkeypatch.setattr(ctgan_service, "CTGANService", lambda: _FakeCTGAN())
    monkeypatch.setattr(timegan_service, "TimeGANService", lambda: _FakeTimeGAN())
    import lib.synthetic.research_cohort_service as rcs
    monkeypatch.setattr(rcs, "CTGANService", lambda: _FakeCTGAN())
    monkeypatch.setattr(rcs, "TimeGANService", lambda: _FakeTimeGAN())
    return True
