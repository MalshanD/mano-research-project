"""
Unit + integration tests for the Adaptive Intervention Rehearsal Engine.

Strategy
--------
The engine composes four singleton services
(`RiskPredictionService`, `InterventionService`, `CTGANService`,
`TimeGANService`) plus the `predict_with_uncertainty` helper. We
monkey-patch all of them with deterministic stubs so the unit tests
don't require the real `.pth` / `.pkl` files in CI.

Test coverage
-------------
1. **Smoke test** — a default request returns a structurally valid plan
   with three branches and the expected day counts.
2. **Determinism** — same seed → byte-identical trajectories.
3. **Goal attainment** — when stub LSTM returns improving probabilities,
   `days_to_goal` is set; when it doesn't, it's None.
4. **Swap rule** — when the realistic trajectory does not improve enough
   by chunk boundary, a SwapEvent is emitted; the swap-decision branch
   is identifiable.
5. **Adherence labelling** — three branches get pessimistic / realistic /
   optimistic labels in order of adherence value.
6. **Synthesis** — `synthesize_missing_data=True` with no patient_state
   pulls from CTGAN + TimeGAN stubs and tags provenance correctly.
7. **Confidence band** — when the LSTM model isn't available the band
   gracefully degrades to zero-spread so the response still validates.
8. **Horizon flooring** — non-multiple-of-7 horizons are floored to a
   multiple of 7 days.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
import pytest

from lib.synthetic import rehearsal_service
from schemas.synthetic.rehearsal_schema import (
    InterventionSpec,
    PlanGoal,
    RehearsalRequest,
)
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
    StaticFeatures,
)


# ─── Test stubs for the frozen-model singletons ──────────────────────────────


class _StubRisk:
    """Risk service stub. Returns class probabilities that improve linearly
    with the mean ``stress_level`` of the input window — this lets us
    construct deterministic test scenarios.
    """

    def __init__(self, improving: bool = True) -> None:
        self.improving = improving
        self.calls = 0
        self.model = object()  # truthy for the band-loaded check

    def predict(self, dynamic_data: np.ndarray, static_data: np.ndarray) -> dict:
        self.calls += 1
        # stress_level is feature index 3 in the (1, T, 4) tensor
        mean_stress = float(np.mean(dynamic_data[..., 3]))
        # As stress drops, low-risk probability rises.
        low_p = float(np.clip(1.0 - mean_stress, 0.0, 1.0))
        high_p = float(np.clip(mean_stress, 0.0, 1.0))
        med_p = float(np.clip(1.0 - low_p - high_p, 0.0, 1.0))
        # Renormalise (defensive).
        total = low_p + med_p + high_p
        if total > 0:
            low_p, med_p, high_p = low_p / total, med_p / total, high_p / total
        risk_class = int(np.argmax([low_p, med_p, high_p]))
        return {
            "risk_class": risk_class,
            "confidence": max(low_p, med_p, high_p),
            "probabilities": [low_p, med_p, high_p],
        }


class _StubIntervention:
    """Intervention service stub.

    ``simulate_outcome`` projects 7 days forward from the input history's
    last day, applying intensity-scaled stress decay and a small
    sleep-hours boost — modelling Seq2Seq's "given history → output
    future" contract, not a perturbation of the input.
    ``get_prescription`` is deterministic — always CBT at intensity 0.6 —
    so a single rehearsal is reproducible across calls. The candidate
    fan-out in ``_ppo_top_k`` produces the alternate arms by hand.
    """

    def __init__(self) -> None:
        self.simulate_calls = 0
        self.prescribe_calls = 0

    def simulate_outcome(
        self, patient_dynamic: np.ndarray, intervention_type: int, intensity: float
    ) -> np.ndarray:
        self.simulate_calls += 1
        last_day = patient_dynamic[0, -1]
        decay = 0.06 * float(intensity)        # stress reduction per day
        sleep_boost = 0.05 * float(intensity)
        proj = np.zeros((1, 7, 4), dtype=np.float32)
        for d in range(7):
            proj[0, d, 0] = float(np.clip(last_day[0] + sleep_boost * (d + 1), 0.0, 24.0))
            proj[0, d, 1] = float(last_day[1])
            proj[0, d, 2] = float(last_day[2])
            proj[0, d, 3] = float(np.clip(last_day[3] - decay * (d + 1), 0.0, 1.0))
        return proj

    def get_prescription(self, dynamic_flat: np.ndarray, static_flat: np.ndarray) -> dict:
        self.prescribe_calls += 1
        return {"intervention_id": int(InterventionType.CBT), "intensity": 0.6, "confidence": 0.7}


class _StubCTGAN:
    def is_loaded(self) -> bool:
        return True

    def generate(self, num_samples: int = 1) -> pd.DataFrame:
        # Return one row of 20 numeric columns.
        return pd.DataFrame([[0.5] * 20], columns=[f"col_{i}" for i in range(20)])


class _StubTimeGAN:
    def is_loaded(self) -> bool:
        return True

    def generate_denormalized(self, num_samples: int = 1) -> np.ndarray:
        # 1 sample × 7 days × 4 channels with realistic-ish baseline.
        sample = np.zeros((1, 7, 4), dtype=np.float32)
        sample[0, :, 0] = 7.0          # sleep_hours
        sample[0, :, 1] = 0.55         # sleep_quality
        sample[0, :, 2] = 72.0         # heart_rate
        sample[0, :, 3] = 0.45         # stress_level
        return sample


@dataclass
class _StubClassStatistic:
    class_index: int
    class_name: str
    mean: float
    std: float
    min: float
    max: float


@dataclass
class _StubUncertaintyResult:
    class_statistics: list


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _seven_day_history(stress: float = 0.5) -> List[DayVitals]:
    return [
        DayVitals(sleep_hours=6.5, sleep_quality=0.55, heart_rate=72.0, stress_level=stress)
        for _ in range(7)
    ]


def _patient_state(stress: float = 0.5) -> PatientState:
    return PatientState(
        static_data=StaticFeatures(features=[0.1] * 20),
        dynamic_history=_seven_day_history(stress),
    )


@pytest.fixture
def stubbed_engine(monkeypatch):
    """Wire deterministic stubs onto every singleton the engine touches."""
    risk = _StubRisk()
    intervention = _StubIntervention()
    ctgan = _StubCTGAN()
    timegan = _StubTimeGAN()

    monkeypatch.setattr(rehearsal_service, "RiskPredictionService", lambda: risk)
    monkeypatch.setattr(rehearsal_service, "InterventionService", lambda: intervention)
    monkeypatch.setattr(rehearsal_service, "CTGANService", lambda: ctgan)
    monkeypatch.setattr(rehearsal_service, "TimeGANService", lambda: timegan)

    # Replace MC dropout with a deterministic banded output.
    def _mc_stub(model, dynamic_np, static_np, n_samples=20):
        mean_stress = float(np.mean(dynamic_np[..., 3]))
        return _StubUncertaintyResult(class_statistics=[
            _StubClassStatistic(0, "Low", 1.0 - mean_stress, 0.05, max(0.0, 1.0 - mean_stress - 0.05), min(1.0, 1.0 - mean_stress + 0.05)),
            _StubClassStatistic(1, "Medium", 0.0, 0.0, 0.0, 0.0),
            _StubClassStatistic(2, "High", mean_stress, 0.05, max(0.0, mean_stress - 0.05), min(1.0, mean_stress + 0.05)),
        ])

    monkeypatch.setattr(rehearsal_service, "predict_with_uncertainty", _mc_stub)

    return {"risk": risk, "intervention": intervention, "ctgan": ctgan, "timegan": timegan}


# ─── 1. Smoke test ───────────────────────────────────────────────────────────


def test_smoke_default_request_returns_valid_plan(stubbed_engine):
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(stress=0.7),
        seed=1234,
    ))
    assert plan.plan_id
    assert plan.horizon_days == 14
    assert len(plan.trajectories) == 3
    for branch in plan.trajectories:
        assert len(branch.days) == 14
        assert len(branch.high_risk_probability_curve) == 14
    assert plan.primary_intervention.intervention_type == InterventionType.CBT
    # Confidence band populated at three checkpoints (1, midway, last).
    assert plan.confidence_band.checkpoints == [1, 7, 14]


# ─── 2. Determinism ──────────────────────────────────────────────────────────


def test_seed_makes_plans_deterministic(stubbed_engine):
    req = RehearsalRequest(patient_state=_patient_state(stress=0.65), seed=42)
    plan_a = rehearsal_service.rehearse_plan(req)
    plan_b = rehearsal_service.rehearse_plan(req)

    # plan_id rotates per call; everything else must match.
    assert plan_a.plan_id != plan_b.plan_id
    for t_a, t_b in zip(plan_a.trajectories, plan_b.trajectories):
        for d_a, d_b in zip(t_a.days, t_b.days):
            assert d_a.vitals.sleep_hours == d_b.vitals.sleep_hours
            assert d_a.vitals.stress_level == d_b.vitals.stress_level
            assert d_a.skipped_due_to_adherence == d_b.skipped_due_to_adherence


# ─── 3. Goal attainment ──────────────────────────────────────────────────────


def test_goal_attained_when_trajectory_improves(stubbed_engine):
    # Stress starts high but the stub Seq2Seq decays it day-by-day; with
    # primary intervention at intensity 0.6 the goal of LOW risk should
    # be reached well within a 14-day horizon on the realistic branch.
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(stress=0.7),
        goal=PlanGoal(target_risk_level=RiskLevel.LOW, target_window_days=14),
        seed=7,
    ))
    realistic = next(b for b in plan.trajectories if b.label == "realistic")
    # The stub Seq2Seq monotonically reduces stress; the LSTM stub flips
    # to LOW the moment mean stress drops below the medium threshold.
    assert realistic.days_to_goal is not None
    assert realistic.days_to_goal <= 14


def test_goal_missed_when_starting_stress_low_but_target_unrealistic(stubbed_engine):
    """Edge case: with a 7-day horizon and very high starting stress + low
    intensity, the realistic branch may not converge to LOW risk.
    """
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(stress=0.99),
        candidate_interventions=[
            InterventionSpec(intervention_type=InterventionType.CONTROL, intensity=0.1),
        ],
        adherence_levels=[0.6, 0.8, 0.95],
        horizon_days=7,
        seed=99,
    ))
    realistic = next(b for b in plan.trajectories if b.label == "realistic")
    # Either it doesn't reach the goal, or attainment is the final day.
    assert realistic.days_to_goal in (None, 7)


# ─── 4. Swap rule ────────────────────────────────────────────────────────────


def test_swap_event_emitted_when_trajectory_off_goal(stubbed_engine):
    """Force the off-track condition by setting an aggressive
    min_midway_delta — the realistic branch can't possibly satisfy it,
    so a swap must fire at the chunk boundary.
    """
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(stress=0.5),
        goal=PlanGoal(min_midway_delta=0.99, target_window_days=14),
        seed=11,
    ))
    assert len(plan.swap_events) >= 1
    swap = plan.swap_events[0]
    assert swap.from_intervention.intervention_type != swap.to_intervention.intervention_type
    assert swap.at_day == 7  # only chunk boundary in a 14-day plan
    assert "below the" in swap.reason.lower() or "threshold" in swap.reason.lower()


def test_no_swap_when_trajectory_on_track(stubbed_engine):
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(stress=0.6),
        goal=PlanGoal(min_midway_delta=0.001, target_window_days=14),
        seed=22,
    ))
    # Improvement only needs to exceed 0.001 by midway — easy.
    assert plan.swap_events == []


# ─── 5. Adherence labelling ──────────────────────────────────────────────────


def test_three_branches_labelled_correctly(stubbed_engine):
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(),
        adherence_levels=[0.6, 0.8, 0.95],
        seed=3,
    ))
    labels = [t.label for t in plan.trajectories]
    assert labels == ["pessimistic", "realistic", "optimistic"]


# ─── 6. Synthesis ────────────────────────────────────────────────────────────


def test_synthesize_missing_data_pulls_from_ctgan_timegan(stubbed_engine):
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=None,
        synthesize_missing_data=True,
        seed=5,
    ))
    assert plan.patient_summary.static_feature_provenance == "ctgan_synthesized"
    assert plan.patient_summary.vitals_provenance == "timegan_synthesized"


def test_missing_state_without_synth_flag_raises(stubbed_engine):
    with pytest.raises(ValueError):
        rehearsal_service.rehearse_plan(RehearsalRequest(
            patient_state=None,
            synthesize_missing_data=False,
        ))


# ─── 7. Confidence band degrades when model unavailable ──────────────────────


def test_confidence_band_degrades_when_lstm_unloaded(monkeypatch, stubbed_engine):
    risk = stubbed_engine["risk"]
    risk.model = None

    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(),
        seed=8,
    ))
    assert plan.confidence_band.n_passes == 0
    # Bands collapsed to a single value (zero spread) when model is None.
    spread = max(b - a for a, b in zip(plan.confidence_band.low_p5, plan.confidence_band.high_p95))
    assert spread == 0


# ─── 8. Horizon flooring ─────────────────────────────────────────────────────


def test_horizon_floored_to_multiple_of_seven(stubbed_engine):
    # Pydantic schema floor is 7; pick 13 which floors to 7.
    plan = rehearsal_service.rehearse_plan(RehearsalRequest(
        patient_state=_patient_state(),
        horizon_days=13,
        seed=4,
    ))
    assert plan.horizon_days == 7
    assert len(plan.trajectories[0].days) == 7
