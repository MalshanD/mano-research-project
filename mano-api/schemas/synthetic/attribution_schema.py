"""
Pydantic schemas for the Outcome Attribution Engine.

The engine answers a causal-inference question that no other surface in
this codebase answers:

    "When my risk improved, how much of the improvement was *caused by*
     the intervention, versus what would have happened anyway?"

Concretely: we project the patient's next 7 days under two arms — the
prescribed intervention and the null (Control, intensity 0) — and
attribute the observed delta-risk between them to the intervention.
The remaining delta against the baseline is what would have happened
without us doing anything.

This is the kind of separation clinicians do mentally with experience.
Surfacing it explicitly turns "I felt better after my walk" into a
defensible answer about whether the walk caused the change or whether
the patient was already on a recovering trajectory.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
)


class AttributionRequest(BaseModel):
    """Input: a patient state + the intervention they actually took."""

    patient_state: PatientState
    intervention_type: InterventionType
    intensity: float = Field(0.5, ge=0.1, le=1.0)
    horizon_days: int = Field(
        7, ge=3, le=14,
        description="Days to project under both arms. Capped at 14 (two "
                    "Seq2Seq chunks) — beyond that the null-counterfactual "
                    "drift estimate becomes too noisy to be useful.",
    )


class AttributionDecomposition(BaseModel):
    """Numeric decomposition of the observed delta-risk."""

    baseline_high_risk_probability: float = Field(
        ...,
        description="High-risk probability today, before either projection runs.",
    )
    null_projection_high_risk_probability: float = Field(
        ...,
        description="High-risk probability at the horizon end if no "
                    "intervention is applied (Seq2Seq with Control + 0 intensity).",
    )
    intervention_projection_high_risk_probability: float = Field(
        ...,
        description="High-risk probability at the horizon end with the "
                    "actual intervention applied.",
    )

    total_observed_change: float = Field(
        ...,
        description="intervention_projection − baseline. Negative = improvement.",
    )
    baseline_drift: float = Field(
        ...,
        description="null_projection − baseline. The change that would "
                    "have happened with no intervention (regression to the "
                    "mean, baseline drift, etc.).",
    )
    intervention_effect: float = Field(
        ...,
        description="intervention_projection − null_projection. The "
                    "*causal* effect attributable to the intervention.",
    )

    fraction_attributable_to_intervention: Optional[float] = Field(
        None, ge=-2.0, le=2.0,
        description="intervention_effect / total_observed_change. Bounded "
                    "to [-2, 2] to keep the report readable when the "
                    "denominator is small. None when the denominator is "
                    "below the numerical noise floor.",
    )


class AttributionTrajectory(BaseModel):
    """The day-by-day high-risk probability curves for each arm — useful
    for rendering a side-by-side line chart in the UI."""

    null_arm_high_risk_curve: List[float]
    intervention_arm_high_risk_curve: List[float]


class AttributionReport(BaseModel):
    """Full attribution response."""

    horizon_days: int
    baseline_risk_class: RiskLevel
    decomposition: AttributionDecomposition
    trajectories: AttributionTrajectory

    interpretation: str = Field(
        ...,
        description="Plain-English summary, e.g. 'The intervention "
                    "accounts for 78 % of the projected improvement; the "
                    "remaining 22 % would have happened with no action.'",
    )

    source: str = Field(
        "live",
        description="Provenance tag — 'live' from the frozen models.",
    )
