"""
MC Dropout Uncertainty — Schemas

Monte Carlo Dropout for uncertainty quantification.
Runs the LSTM risk predictor N times with dropout enabled,
producing a distribution of predictions instead of a single point estimate.
"""
from pydantic import BaseModel, Field
from typing import List

from schemas.synthetic.simulation_schema import PatientState, RiskPredictionResponse


class UncertaintyRequest(BaseModel):
    """Request for MC Dropout uncertainty estimation."""
    patient_state: PatientState
    n_samples: int = Field(default=30, ge=5, le=100, description="Number of MC forward passes")


class ClassDistribution(BaseModel):
    """Statistics for one risk class across MC samples."""
    risk_class: str
    mean_probability: float
    std_probability: float
    min_probability: float
    max_probability: float


class UncertaintyResponse(BaseModel):
    """MC Dropout uncertainty report."""
    # Point estimate (standard single-pass prediction)
    point_estimate: RiskPredictionResponse

    # MC Dropout statistics
    n_samples: int
    class_distributions: List[ClassDistribution]

    # Predictive entropy (higher = more uncertain)
    predictive_entropy: float = Field(description="Shannon entropy of mean class probs")
    mutual_information: float = Field(description="Epistemic uncertainty (model uncertainty)")

    # Stability
    prediction_stability: float = Field(
        description="Fraction of MC samples that agree with the point estimate (0-1)"
    )
    is_reliable: bool = Field(
        description="True if stability > 0.7 and entropy < 1.0"
    )

    # Explanation
    uncertainty_summary: str
