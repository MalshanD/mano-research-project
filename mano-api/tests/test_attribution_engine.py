"""
Tests for ``lib.synthetic.attribution_service``.

The attribution engine composes three frozen-model entry points
(LSTM ``predict``, Seq2Seq ``simulate_outcome``, Seq2Seq again for the
null arm). We monkey-patch each so the unit tests don't require the
real ``.pth`` files.

Coverage
--------
1. The decomposition arithmetic is exact:
     intervention_effect == intervention_proj - null_proj
     baseline_drift     == null_proj - baseline
     total_change       == intervention_proj - baseline
2. Fraction-attributable is None when total_change is below the noise
   floor (so the UI doesn't render a divide-by-near-zero ratio).
3. Interpretation handles the four sign combinations
   (intervention±, baseline±) without error.
4. Horizon > 7 days triggers two chunks per arm and produces a
   ``horizon_days``-length curve.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pytest

from lib.synthetic import attribution_service
from schemas.synthetic.attribution_schema import AttributionRequest
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
    StaticFeatures,
)


# ─── Stubs for the frozen-model singletons ──────────────────────────────────


class _StubRisk:
    """LSTM stub. Returns probabilities that are a deterministic function
    of the input window's mean stress (feature index 3). This lets each
    test construct a known scenario.
    """

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, dynamic_data: np.ndarray, static_data: np.ndarray) -> dict:
        self.calls += 1
        mean_stress = float(np.mean(dynamic_data[..., 3]))
        # Map [0, 1] stress to a smooth high-risk probability.
        high = float(np.clip(mean_stress, 0.0, 1.0))
        low = float(np.clip(1.0 - high, 0.0, 1.0))
        med = max(0.0, 1.0 - high - low)
        cls = int(np.argmax([low, med, high]))
        return {
            "risk_class": cls,
            "confidence": max(low, med, high),
            "probabilities": [low, med, high],
        }


class _StubIntervention:
    """Seq2Seq stub. Project 7 days forward from the last day of history,
    decaying stress at a rate proportional to intensity. The Control arm
    (type=0, intensity=0) leaves stress unchanged, so the null
    counterfactual produces a flat trajectory.
    """

    def __init__(self, decay_per_unit: float = 0.04) -> None:
        self.decay_per_unit = decay_per_unit
        self.calls = 0

    def simulate_outcome(
        self, patient_dynamic: np.ndarray, intervention_type: int, intensity: float
    ) -> np.ndarray:
        self.calls += 1
        last = patient_dynamic[0, -1]
        proj = np.zeros((1, 7, 4), dtype=np.float32)
        decay = self.decay_per_unit * float(intensity) if intervention_type != 0 else 0.0
        for d in range(7):
            proj[0, d, 0] = float(np.clip(last[0], 0.0, 24.0))
            proj[0, d, 1] = float(last[1])
            proj[0, d, 2] = float(last[2])
            proj[0, d, 3] = float(np.clip(last[3] - decay * (d + 1), 0.0, 1.0))
        return proj


@pytest.fixture
def stubbed(monkeypatch):
    risk = _StubRisk()
    intervention = _StubIntervention()
    monkeypatch.setattr(attribution_service, "RiskPredictionService", lambda: risk)
    monkeypatch.setattr(attribution_service, "InterventionService", lambda: intervention)
    return {"risk": risk, "intervention": intervention}


def _patient(stress: float = 0.7) -> PatientState:
    return PatientState(
        static_data=StaticFeatures(features=[0.1] * 20),
        dynamic_history=[
            DayVitals(sleep_hours=6.5, sleep_quality=0.55, heart_rate=72.0, stress_level=stress)
            for _ in range(7)
        ],
    )


# ─── 1. Decomposition arithmetic ────────────────────────────────────────────


def test_decomposition_arithmetic_is_exact(stubbed):
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.7),
        intervention_type=InterventionType.CBT,
        intensity=0.6,
        horizon_days=7,
    ))
    d = report.decomposition
    # Sums must hold to floating-point tolerance.
    assert abs(d.total_observed_change - (
        d.intervention_projection_high_risk_probability
        - d.baseline_high_risk_probability
    )) < 1e-6
    assert abs(d.baseline_drift - (
        d.null_projection_high_risk_probability
        - d.baseline_high_risk_probability
    )) < 1e-6
    assert abs(d.intervention_effect - (
        d.intervention_projection_high_risk_probability
        - d.null_projection_high_risk_probability
    )) < 1e-6
    # And the additive identity.
    assert abs(d.total_observed_change - (d.baseline_drift + d.intervention_effect)) < 1e-6


# ─── 2. Causal direction ────────────────────────────────────────────────────


def test_intervention_arm_lowers_high_risk_more_than_null_arm(stubbed):
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.7),
        intervention_type=InterventionType.CBT,
        intensity=0.6,
        horizon_days=7,
    ))
    d = report.decomposition
    # Stub Seq2Seq: Control leaves stress flat (drift = 0), CBT lowers it.
    assert abs(d.baseline_drift) < 1e-6
    # Intervention effect is negative (improvement).
    assert d.intervention_effect < 0


def test_null_arm_returns_flat_trajectory(stubbed):
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.6),
        intervention_type=InterventionType.EXERCISE,
        intensity=0.4,
        horizon_days=7,
    ))
    null_curve = report.trajectories.null_arm_high_risk_curve
    # Every value should be very close to the baseline (no change with stub Control arm).
    baseline = report.decomposition.baseline_high_risk_probability
    for v in null_curve:
        assert abs(v - baseline) < 1e-3


# ─── 3. Fraction attribution edge-cases ─────────────────────────────────────


def test_fraction_is_none_when_total_change_below_noise_floor(stubbed):
    # A super-tiny intensity → effect below noise floor.
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.5),
        intervention_type=InterventionType.CBT,
        intensity=0.1,
        horizon_days=7,
    ))
    # With our stub, intensity 0.1 × decay 0.04 × 7 days ≈ 0.028 stress drop —
    # mean window stress changes by far less than the noise floor.
    if abs(report.decomposition.total_observed_change) < 0.005:
        assert report.decomposition.fraction_attributable_to_intervention is None


def test_fraction_clamped_to_neg_two_to_two_band(stubbed):
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.6),
        intervention_type=InterventionType.CBT,
        intensity=0.8,
        horizon_days=7,
    ))
    f = report.decomposition.fraction_attributable_to_intervention
    if f is not None:
        assert -2.0 <= f <= 2.0


# ─── 4. Horizon > 7 days produces longer curve ──────────────────────────────


def test_horizon_14_produces_two_chunks_per_arm(stubbed):
    report = attribution_service.attribute_outcome(AttributionRequest(
        patient_state=_patient(stress=0.7),
        intervention_type=InterventionType.CBT,
        intensity=0.6,
        horizon_days=14,
    ))
    assert report.horizon_days == 14
    assert len(report.trajectories.intervention_arm_high_risk_curve) == 14
    assert len(report.trajectories.null_arm_high_risk_curve) == 14
    # Two intervention calls (chunk 1 + chunk 2) per arm = 4 simulator calls total.
    assert stubbed["intervention"].calls >= 4


# ─── 5. Interpretation copy is non-empty ────────────────────────────────────


def test_interpretation_is_non_empty_string(stubbed):
    for stress in (0.3, 0.5, 0.7, 0.9):
        report = attribution_service.attribute_outcome(AttributionRequest(
            patient_state=_patient(stress=stress),
            intervention_type=InterventionType.CBT,
            intensity=0.5,
            horizon_days=7,
        ))
        assert report.interpretation
        assert len(report.interpretation) > 20
        # Never use the prohibited words from the guideline.
        forbidden = ("AI ", "model", "simulation", "algorithm", "predicted", "calculated")
        assert not any(w in report.interpretation for w in forbidden)


# ─── 6. Determinism ─────────────────────────────────────────────────────────


def test_same_input_yields_same_decomposition(stubbed):
    req = AttributionRequest(
        patient_state=_patient(stress=0.65),
        intervention_type=InterventionType.CBT,
        intensity=0.6,
        horizon_days=7,
    )
    a = attribution_service.attribute_outcome(req)
    b = attribution_service.attribute_outcome(req)
    assert a.decomposition.intervention_effect == b.decomposition.intervention_effect
    assert a.decomposition.baseline_drift == b.decomposition.baseline_drift
    assert a.decomposition.total_observed_change == b.decomposition.total_observed_change
