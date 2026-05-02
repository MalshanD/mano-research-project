"""
What-If Lifestyle Simulator — Schemas

Allows users to specify hypothetical lifestyle targets and receive
a side-by-side comparison: baseline trajectory vs modified trajectory.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

# Reuse existing schemas — no duplication
from schemas.synthetic.simulation_schema import (
    PatientState,
    DayVitals,
    RiskPredictionResponse,
)


# --- INPUT ---

class LifestyleTargets(BaseModel):
    """
    The user's hypothetical lifestyle values.
    All fields are optional — only override what you want to change.
    """
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Target sleep hours per night")
    sleep_quality: Optional[float] = Field(None, ge=0, le=1, description="Target sleep quality (0-1)")
    heart_rate: Optional[float] = Field(None, ge=40, le=200, description="Target resting heart rate")
    stress_level: Optional[float] = Field(None, ge=0, le=1, description="Target stress level (0=calm, 1=max)")


class WhatIfRequest(BaseModel):
    """
    The 'What If I changed my lifestyle?' question.
    """
    patient_state: PatientState
    lifestyle_targets: LifestyleTargets
    blend_days: int = Field(
        default=3,
        ge=1,
        le=7,
        description="How many of the most recent days to blend toward the target (1-7)"
    )


# --- OUTPUT ---

class TrajectoryDay(BaseModel):
    """A single day in the projected trajectory."""
    day: int
    sleep_hours: float
    sleep_quality: float
    heart_rate: float
    stress_level: float


class WhatIfResponse(BaseModel):
    """Side-by-side comparison of baseline vs modified future."""
    # 7-day projected trajectories
    baseline_trajectory: List[TrajectoryDay]
    modified_trajectory: List[TrajectoryDay]

    # Risk predictions on projected futures
    baseline_risk: RiskPredictionResponse
    modified_risk: RiskPredictionResponse

    # Summary
    risk_delta: float = Field(description="Positive = improvement (risk decreased)")
    improvement_summary: str = Field(description="Human-readable summary of changes")
