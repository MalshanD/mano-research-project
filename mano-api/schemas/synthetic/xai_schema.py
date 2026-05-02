"""
XAI (Explainable AI) — Schemas

Provides schemas for risk factor attribution using Integrated Gradients.
Returns per-feature, per-day importance scores explaining WHY the LSTM
predicted a particular risk class.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
)


# --- OUTPUT ---

class FeatureAttribution(BaseModel):
    """Attribution score for a single feature on a single day."""
    day: int = Field(description="Day index (1-7)")
    feature: str = Field(description="Feature name")
    attribution: float = Field(description="Signed attribution (positive = increases risk)")
    normalized: float = Field(description="Normalized absolute attribution (0-1)")


class FeatureSummary(BaseModel):
    """Aggregated importance of a single feature across all days."""
    feature: str
    total_attribution: float = Field(description="Sum of absolute attributions across days")
    direction: str = Field(description="'risk-increasing' or 'risk-decreasing'")
    rank: int = Field(description="1 = most important")


class StaticAttribution(BaseModel):
    """Attribution for a static (demographic) feature."""
    feature_index: int
    attribution: float
    normalized: float


class XAIResponse(BaseModel):
    """Full explainability report for a risk prediction."""
    # The prediction being explained
    risk_prediction: RiskPredictionResponse

    # Per-day, per-feature heatmap data (7 days × 4 features = 28 entries)
    temporal_attributions: List[FeatureAttribution]

    # Ranked feature importance (4 features, ranked by total impact)
    feature_rankings: List[FeatureSummary]

    # Top static feature attributions (top 5 most impactful demographics)
    static_attributions: List[StaticAttribution]

    # Explanation summary
    explanation: str = Field(description="Human-readable explanation of the prediction")
