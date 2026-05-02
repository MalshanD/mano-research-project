"""
Batch Simulation Schemas.
For comparing all 5 interventions on a single patient in one API call.
"""
from pydantic import BaseModel, Field
from typing import List

from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
    DayVitals,
)


class InterventionComparison(BaseModel):
    """Result of one intervention in the batch comparison."""
    intervention_name: str
    intervention_id: int
    intensity: float
    original_risk: RiskPredictionResponse
    projected_risk: RiskPredictionResponse
    future_vitals: List[DayVitals]
    risk_reduction_score: float


class BatchSimulationRequest(BaseModel):
    """Request to simulate all 5 interventions at a given intensity."""
    patient_state: PatientState
    intensity: float = Field(
        default=0.7, ge=0.1, le=1.0,
        description="Intensity to test all interventions at (0.1-1.0)"
    )


class BatchSimulationResponse(BaseModel):
    """All 5 interventions compared, ranked by risk reduction."""
    patient_baseline_risk: RiskPredictionResponse
    comparisons: List[InterventionComparison]
    best_intervention: str
    best_risk_reduction: float
