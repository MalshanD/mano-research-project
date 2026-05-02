"""
Next-Best-Action — Schemas

Full closed-loop recommendation: PPO Agent recommends → Seq2Seq simulates
→ LSTM evaluates risk → all interventions compared and ranked.
"""
from pydantic import BaseModel, Field
from typing import List

from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
    DayVitals,
)


class InterventionCandidate(BaseModel):
    """One possible intervention with its simulated outcome."""
    intervention_id: int
    intervention_name: str
    intensity: float = Field(ge=0.1, le=1.0)
    projected_risk: RiskPredictionResponse
    risk_reduction: float = Field(description="Positive = risk decreased vs baseline")
    rank: int = Field(description="1 = best outcome")


class NBAResponse(BaseModel):
    """Full Next-Best-Action response with evidence."""
    # The PPO Agent's recommendation
    recommended_intervention: str
    recommended_intensity: float
    is_ppo_top_ranked: bool = Field(
        description="Whether the PPO's choice also has the best simulated outcome"
    )

    # Current baseline risk
    baseline_risk: RiskPredictionResponse

    # All interventions ranked by simulated outcome
    candidates: List[InterventionCandidate]

    # Reasoning
    reasoning: str
    confidence_note: str = Field(
        description="Note about agreement between PPO and simulation ranking"
    )
