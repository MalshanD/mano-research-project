"""
Pydantic schemas for the multi-horizon trajectory forecasting API.

Only input/output shapes live here. All math lives in
``lib/synthetic/trajectory_service.py``.
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


class TrajectoryRequest(BaseModel):
    patient_state: PatientState
    intervention_type: InterventionType = Field(
        default=InterventionType.CONTROL,
        description=(
            "Intervention applied throughout the forecast horizon. "
            "Use CONTROL (0) for a natural-progression baseline forecast."
        ),
    )
    intensity: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Intensity scalar passed to the Seq2Seq simulator.",
    )
    horizon_days: int = Field(
        default=14, ge=7, le=28,
        description=(
            "Total days to forecast. The Seq2Seq model natively produces 7 "
            "days; beyond that we extrapolate recursively one 7-day window "
            "at a time."
        ),
    )
    uncertainty_samples: int = Field(
        default=20, ge=0, le=100,
        description=(
            "MC-Dropout samples per day for risk-probability confidence "
            "bands. 0 disables the uncertainty sweep for a faster response."
        ),
    )


class DayForecast(BaseModel):
    day_index: int = Field(..., description="1-indexed day number in the forecast horizon.")
    vitals: DayVitals
    risk_class: RiskLevel
    risk_confidence: float
    risk_probabilities: List[float]
    # Uncertainty band — None when uncertainty_samples == 0
    risk_probability_std: Optional[List[float]] = None
    predictive_entropy: Optional[float] = None
    mutual_information: Optional[float] = None


class TrajectoryResponse(BaseModel):
    horizon_days: int
    intervention: str
    intensity: float
    forecasts: List[DayForecast]
    # Summary rollups the frontend uses for banner-style metrics.
    peak_risk_day: Optional[int] = None
    peak_risk_class: Optional[RiskLevel] = None
    trajectory_shape: str = Field(
        ..., description="Qualitative label: improving | worsening | stable | oscillating",
    )
    notes: List[str] = Field(default_factory=list)
