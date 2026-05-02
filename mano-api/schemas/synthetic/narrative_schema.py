"""
Pydantic schemas for the Future-Self Narrative Engine (v2).

v2 differs from the legacy ``enhanced_c1_route.NarrativeRequest`` in that it
takes a *structured* trajectory summary (aligned with the Phase-1 trajectory
forecasting service) rather than a free-form ``simulation_data`` dict. This
lets the narrative layer reason about trajectory shape, peak-risk day, and
uncertainty — producing richer, more honest narratives.

All LLM-facing free-text fields (``patient_voice``, tone, etc.) are
sanitised in the service layer before being interpolated into a prompt.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import RiskLevel


class NarrativeTone(str, Enum):
    HOPEFUL = "hopeful"
    CLINICAL = "clinical"
    NEUTRAL = "neutral"


class NarrativeLength(str, Enum):
    SHORT = "short"    # ≤ 3 sentences
    MEDIUM = "medium"  # 4–6 sentences
    LONG = "long"      # 7–10 sentences


class TrajectorySummary(BaseModel):
    """Condensed trajectory stats — shaped to mirror TrajectoryResponse."""
    intervention: str = Field(..., description="Intervention label, e.g. 'CBT'.")
    intensity: float = Field(..., ge=0.0, le=1.0)
    horizon_days: int
    trajectory_shape: Literal["improving", "worsening", "stable", "oscillating"]
    peak_risk_day: Optional[int] = None
    peak_risk_class: Optional[RiskLevel] = None
    mean_high_risk_probability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Average P(high risk) across the forecast horizon.",
    )


class NarrativeRequest(BaseModel):
    trajectory: TrajectorySummary
    tone: NarrativeTone = NarrativeTone.HOPEFUL
    length: NarrativeLength = NarrativeLength.MEDIUM
    patient_voice: Optional[str] = Field(
        default=None, max_length=500,
        description=(
            "Optional free-text note from the patient (preferences, context). "
            "Sanitised before being appended to the prompt."
        ),
    )


class NarrativeResponse(BaseModel):
    narrative: str
    intervention: str
    tone: NarrativeTone
    length: NarrativeLength
    source: str = Field(..., description="live | cached | fallback")
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider that served this response (groq, gemini, hf, template).",
    )
    notes: List[str] = Field(default_factory=list)
