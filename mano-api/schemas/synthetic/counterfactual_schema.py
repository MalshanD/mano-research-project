"""
Pydantic schemas for intervention counterfactual reasoning.

Contract
--------
The caller supplies a ``factual`` arm (what the patient is currently on) and
a ``counterfactual`` arm (what the clinician / user is considering). The API
rolls the frozen Seq2Seq forward for both arms, classifies each day's risk
with the frozen LSTM, and returns a side-by-side comparison plus an
aggregate effect-size metric (risk_reduction_score).

This is distinct from ``what_if_router`` which handles *lifestyle-target*
counterfactuals (vitals modifications). That tool answers "what if I slept
more". This tool answers "what if the clinician prescribed CBT instead of
Medication".

All math sits in ``lib/synthetic/counterfactual_service.py``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
)


class InterventionArm(BaseModel):
    """One side of the counterfactual — factual or counterfactual treatment."""
    intervention_type: InterventionType
    intensity: float = Field(0.5, ge=0.0, le=1.0)


class CounterfactualRequest(BaseModel):
    patient_state: PatientState
    factual: InterventionArm = Field(
        ...,
        description="The treatment the patient is currently on (baseline).",
    )
    counterfactual: InterventionArm = Field(
        ...,
        description="The alternative treatment being considered.",
    )
    horizon_days: int = Field(
        default=14, ge=7, le=28,
        description=(
            "Forecast horizon. Beyond 7 days the Seq2Seq is rolled recursively "
            "(see trajectory_service)."
        ),
    )
    uncertainty_samples: int = Field(
        default=0, ge=0, le=100,
        description=(
            "MC-Dropout samples per day per arm. 0 disables uncertainty for a "
            "faster response; non-zero surfaces a risk-probability band."
        ),
    )


class DayRiskSummary(BaseModel):
    day_index: int
    risk_class: RiskLevel
    risk_confidence: float
    risk_probabilities: List[float]
    predictive_entropy: Optional[float] = None


class InterventionOutcome(BaseModel):
    intervention_name: str
    intervention_type: InterventionType
    intensity: float
    horizon_days: int
    forecast_vitals: List[DayVitals]
    risk_trajectory: List[DayRiskSummary]
    final_risk_class: RiskLevel
    final_risk_probabilities: List[float]
    mean_high_risk_probability: float
    trajectory_shape: str


class CounterfactualResponse(BaseModel):
    factual: InterventionOutcome
    counterfactual: InterventionOutcome

    # Effect-size summary — how much better/worse is the counterfactual?
    risk_reduction_score: float = Field(
        ...,
        description=(
            "factual_mean_high_risk - counterfactual_mean_high_risk. "
            "Positive = counterfactual is better; negative = factual is better."
        ),
    )
    risk_reduction_per_day: List[float] = Field(
        ...,
        description="Per-day (factual high-risk prob - counterfactual high-risk prob).",
    )
    counterfactual_is_better: bool

    # Mechanism: which vitals feature accounts for the most divergence.
    vitals_divergence: Dict[str, float] = Field(
        ...,
        description="Per-feature mean absolute divergence between arms.",
    )
    dominant_feature: Optional[str] = Field(
        None,
        description="Feature with the largest divergence between arms.",
    )

    interpretation: str
    notes: List[str] = Field(default_factory=list)
