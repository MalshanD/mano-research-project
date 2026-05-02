"""
NLP Clinical Reports — Schemas

Auto-generates structured clinical narratives from patient data,
risk predictions, and intervention outcomes.

NOTE: Uses template-based NLP (no external LLM API dependency).
This keeps the system self-contained and avoids API costs.
An LLM API integration point is provided for future enhancement.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

from schemas.synthetic.simulation_schema import PatientState


class ReportSection(BaseModel):
    """One section of the clinical report."""
    title: str
    content: str
    severity: str = Field(
        default="info",
        description="info, warning, or critical"
    )


class ClinicalReportRequest(BaseModel):
    """Request for clinical report generation."""
    patient_state: PatientState
    patient_name: Optional[str] = Field(default=None)
    patient_age: Optional[int] = Field(default=None)
    patient_gender: Optional[str] = Field(default=None)
    include_recommendations: bool = Field(default=True)


class ClinicalReportResponse(BaseModel):
    """Full clinical report."""
    report_id: str
    generated_at: str
    patient_identifier: str

    # Core sections
    sections: List[ReportSection]

    # Summary
    executive_summary: str
    risk_classification: str
    risk_confidence: float

    # Clinical recommendation
    primary_recommendation: Optional[str] = None
    recommended_intervention: Optional[str] = None

    # Full rendered text
    full_report_text: str
