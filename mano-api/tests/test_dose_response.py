"""
Tests for ``lib.synthetic.dose_response_service``.

The service composes the LSTM and Seq2Seq frozen-model entry points.
We monkey-patch each so the unit tests don't need the real model files.

Coverage
--------
1. Default grid produces six points sorted by intensity.
2. Custom grid passes through unchanged (after clipping + dedup).
3. Sweet spot is detected on a curve that flattens.
4. Sweet spot is None on a strictly monotone curve.
5. Interpretation copy keys correctly off curve shape.
6. Determinism: same input → same curve.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pytest

from lib.synthetic import dose_response_service
from schemas.synthetic.dose_response_schema import DoseResponseRequest
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    StaticFeatures,
)


# ─── Stubs ──────────────────────────────────────────────────────────────────


class _StubRisk:
    def predict(self, dynamic_data: np.ndarray, static_data: np.ndarray) -> dict:
        mean_stress = float(np.mean(dynamic_data[..., 3]))
        high = float(np.clip(mean_stress, 0.0, 1.0))
        low = 1.0 - high
        cls = 0 if low > high else 2
        return {"risk_class": cls, "confidence": max(low, high), "probabilities": [low, 0.0, high]}


class _StubInterventionDiminishing:
    """Seq2Seq stub with sharply-diminishing returns. Curve saturates near
    intensity ≈ 0.5 — that's the sweet spot the engine should detect.
    """

    def __init__(self) -> None:
        self.calls = 0

    def simulate_outcome(self, patient_dynamic, intervention_type, intensity):
        self.calls += 1
        last = patient_dynamic[0, -1]
        proj = np.zeros((1, 7, 4), dtype=np.float32)
        # Saturating curve: ≈ 0 at I=0, asymptotically approaches 0.5 stress drop.
        # exp(-8 * I) decays fast → most of the gain is captured by I=0.5.
        total_drop = 0.5 * (1 - np.exp(-8.0 * float(intensity)))
        per_day = total_drop / 7.0
        for d in range(7):
            proj[0, d, 0] = float(last[0])
            proj[0, d, 1] = float(last[1])
            proj[0, d, 2] = float(last[2])
            proj[0, d, 3] = float(np.clip(last[3] - per_day * (d + 1), 0.0, 1.0))
        return proj


class _StubInterventionLinear:
    """Strictly linear improvement — no sweet spot expected."""

    def __init__(self) -> None:
        self.calls = 0

    def simulate_outcome(self, patient_dynamic, intervention_type, intensity):
        self.calls += 1
        last = patient_dynamic[0, -1]
        proj = np.zeros((1, 7, 4), dtype=np.float32)
        per_day = 0.05 * float(intensity)
        for d in range(7):
            proj[0, d, 0] = float(last[0])
            proj[0, d, 1] = float(last[1])
            proj[0, d, 2] = float(last[2])
            proj[0, d, 3] = float(np.clip(last[3] - per_day * (d + 1), 0.0, 1.0))
        return proj


@pytest.fixture
def stubbed_diminishing(monkeypatch):
    risk = _StubRisk()
    intervention = _StubInterventionDiminishing()
    monkeypatch.setattr(dose_response_service, "RiskPredictionService", lambda: risk)
    monkeypatch.setattr(dose_response_service, "InterventionService", lambda: intervention)
    return {"risk": risk, "intervention": intervention}


@pytest.fixture
def stubbed_linear(monkeypatch):
    risk = _StubRisk()
    intervention = _StubInterventionLinear()
    monkeypatch.setattr(dose_response_service, "RiskPredictionService", lambda: risk)
    monkeypatch.setattr(dose_response_service, "InterventionService", lambda: intervention)
    return {"risk": risk, "intervention": intervention}


def _patient(stress: float = 0.7) -> PatientState:
    return PatientState(
        static_data=StaticFeatures(features=[0.1] * 20),
        dynamic_history=[
            DayVitals(sleep_hours=6.5, sleep_quality=0.55, heart_rate=72.0, stress_level=stress)
            for _ in range(7)
        ],
    )


# ─── 1. Default grid ────────────────────────────────────────────────────────


def test_default_grid_has_six_points_sorted(stubbed_diminishing):
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(stress=0.7),
        intervention_type=InterventionType.CBT,
    ))
    assert len(curve.points) == 6
    intensities = [p.intensity for p in curve.points]
    assert intensities == sorted(intensities)


# ─── 2. Custom grid ─────────────────────────────────────────────────────────


def test_custom_grid_is_clipped_deduped_and_sorted(stubbed_diminishing):
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(),
        intervention_type=InterventionType.EXERCISE,
        dose_grid=[0.5, 0.2, 0.5, -0.3, 1.5, 0.7],
    ))
    intensities = [p.intensity for p in curve.points]
    # Negative clipped to 0; out-of-range clipped to 1; duplicate 0.5 removed.
    assert intensities == sorted(set(intensities))
    assert all(0.0 <= i <= 1.0 for i in intensities)


# ─── 3. Sweet spot detected on diminishing-returns curve ────────────────────


def test_sweet_spot_detected_on_diminishing_curve(stubbed_diminishing):
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(stress=0.8),
        intervention_type=InterventionType.CBT,
        dose_grid=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    ))
    # The diminishing-returns stub flattens past mid-range — sweet spot
    # should be set somewhere in the grid (not None).
    assert curve.sweet_spot_intensity is not None
    assert 0.1 <= curve.sweet_spot_intensity <= 1.0


# ─── 4. No sweet spot on strictly monotone curve ────────────────────────────


def test_no_sweet_spot_on_strictly_monotone_curve(stubbed_linear):
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(stress=0.8),
        intervention_type=InterventionType.EXERCISE,
        dose_grid=[0.1, 0.3, 0.5, 0.7, 0.9],
    ))
    # Linear stub: each step gives a fixed-size gain → sweet_spot stays None.
    assert curve.sweet_spot_intensity is None
    # Curve should be monotonically improving.
    highs = [p.projected_high_risk_probability for p in curve.points]
    for i in range(1, len(highs)):
        assert highs[i] <= highs[i - 1] + 1e-6


# ─── 5. Interpretation copy ────────────────────────────────────────────────


def test_interpretation_mentions_sweet_spot_when_present(stubbed_diminishing):
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(stress=0.8),
        intervention_type=InterventionType.CBT,
    ))
    if curve.sweet_spot_intensity is not None:
        assert "intensity" in curve.interpretation.lower() or "benefit" in curve.interpretation.lower()


def test_interpretation_handles_no_benefit_curve(monkeypatch):
    """When no dose lowers risk vs baseline, the interpretation must say so."""
    class _Anti:
        def simulate_outcome(self, patient_dynamic, intervention_type, intensity):
            last = patient_dynamic[0, -1]
            proj = np.zeros((1, 7, 4), dtype=np.float32)
            for d in range(7):
                proj[0, d, 0] = float(last[0])
                proj[0, d, 1] = float(last[1])
                proj[0, d, 2] = float(last[2])
                # Make stress *go up* with intensity — bad arm.
                proj[0, d, 3] = float(np.clip(last[3] + 0.05 * float(intensity) * (d + 1), 0.0, 1.0))
            return proj

    monkeypatch.setattr(dose_response_service, "RiskPredictionService", lambda: _StubRisk())
    monkeypatch.setattr(dose_response_service, "InterventionService", lambda: _Anti())
    curve = dose_response_service.sweep_dose_response(DoseResponseRequest(
        patient_state=_patient(stress=0.5),
        intervention_type=InterventionType.MEDICATION,
    ))
    assert "different intervention" in curve.interpretation.lower() or "did not" in curve.interpretation.lower() or "none reduced" in curve.interpretation.lower()


# ─── 6. Determinism ─────────────────────────────────────────────────────────


def test_same_input_yields_same_curve(stubbed_diminishing):
    req = DoseResponseRequest(
        patient_state=_patient(stress=0.7),
        intervention_type=InterventionType.CBT,
    )
    a = dose_response_service.sweep_dose_response(req)
    b = dose_response_service.sweep_dose_response(req)
    for pa, pb in zip(a.points, b.points):
        assert pa.projected_high_r