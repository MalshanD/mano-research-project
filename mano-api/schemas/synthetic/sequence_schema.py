"""
Intervention Sequencing — Schemas

Multi-step treatment planning: chain interventions over time.
E.g. "CBT for 7 days → Exercise for 7 days → Wellness App for 7 days"
Each step's projected outcome becomes the next step's input.
"""
from pydantic import BaseModel, Field
from typing import List

from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
    DayVitals,
)


class SequenceStep(BaseModel):
    """One step in the treatment sequence."""
    intervention_type: int = Field(ge=0, le=4, description="0=Control, 1=Wellness, 2=CBT, 3=Exercise, 4=Medication")
    intensity: float = Field(ge=0.1, le=1.0, default=0.5)


class SequenceRequest(BaseModel):
    """Request for multi-step intervention sequencing."""
    patient_state: PatientState
    steps: List[SequenceStep] = Field(min_length=1, max_length=5)


class StepResult(BaseModel):
    """Result of one step in the sequence."""
    step_number: int
    intervention_name: str
    intensity: float
    projected_vitals: List[DayVitals] = Field(description="7-day trajectory for this step")
    risk_after: RiskPredictionResponse
    risk_delta_from_previous: float = Field(description="Change in High-risk prob vs previous step")


class SequenceResponse(BaseModel):
    """Full multi-step treatment plan result."""
    baseline_risk: RiskPredictionResponse
    steps: List[StepResult]
    final_risk: RiskPredictionResponse
    total_risk_reduction: float = Field(description="Baseline High% - Final High%")
    summary: str
