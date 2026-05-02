"""
Schemas for the Clinical Passport PDF generator.

What is a "Clinical Passport"?
------------------------------
A printable, shareable, single-document snapshot of a patient's current
state across the MANO platform. It bundles:

* Risk snapshot — latest LSTM classification + confidence.
* Trajectory — forecasted high-risk probability with uncertainty, if the
  caller supplies a forecast series (we don't re-run the model here;
  callers hand in the numbers to keep the passport pass-through).
* Active interventions — the PPO reranker's top candidates for this
  patient, with the reranker's own explanation strings.
* Care-path phase — longitudinal therapy orchestrator phase plus the
  phase's review cadence and tone recommendations.
* Evidence — a short list of optional citations the caller has already
  surfaced (URLs + titles). The passport never re-fetches PubMed; it
  formats what is provided.
* Narrative — optional future-self paragraph, again pass-through.
* Safety notes — blocked interventions, contraindications, escalation
  flags.

The design goal is that the passport can be re-generated offline on a
frozen snapshot — no live calls out to PubMed, Whisper, etc. Callers that
want fresh data stitch it in before handing the payload to the passport
generator.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.reranker_schema import RerankedCandidate, RerankerWeights


class PassportEvidenceItem(BaseModel):
    """One evidence citation included in the passport."""
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    year: Optional[int] = None
    summary: Optional[str] = None


class PassportTrajectoryPoint(BaseModel):
    """One forecast horizon point."""
    day: int = Field(..., ge=0, le=365)
    mean_high_risk_probability: float = Field(..., ge=0.0, le=1.0)
    lower_ci: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    upper_ci: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PassportRiskSnapshot(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    high_risk_probability: float = Field(..., ge=0.0, le=1.0)
    medium_risk_probability: float = Field(..., ge=0.0, le=1.0)
    low_risk_probability: float = Field(..., ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    classifier_uncertainty: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="MC-Dropout variance summarised to a single [0,1] score.",
    )


class PassportCarePath(BaseModel):
    phase: Literal["intake", "stabilise", "practice", "integrate", "maintain"]
    phase_started_at: Optional[datetime] = None
    review_cadence_days: int = Field(..., ge=1, le=90)
    recommended_intervention_tones: List[str] = Field(default_factory=list)
    phase_guidance: str = ""


class ClinicalPassportRequest(BaseModel):
    """Everything the passport needs in a single payload.

    Every structured section is optional — the generator renders only what
    is present so the same endpoint can produce a minimal snapshot or a
    full-spectrum report. The only required fields are the identifier and
    the risk snapshot.
    """
    patient_id: str = Field(..., min_length=1, max_length=64)
    patient_display_name: Optional[str] = Field(default=None, max_length=120)
    generated_for: Optional[str] = Field(
        default=None, max_length=120,
        description="Who the passport is for (clinician, patient, researcher).",
    )

    risk_snapshot: PassportRiskSnapshot
    trajectory: List[PassportTrajectoryPoint] = Field(default_factory=list)
    reranker_weights: Optional[RerankerWeights] = None
    ranked_interventions: List[RerankedCandidate] = Field(default_factory=list)
    care_path: Optional[PassportCarePath] = None
    evidence: List[PassportEvidenceItem] = Field(default_factory=list)
    narrative_paragraph: Optional[str] = Field(default=None, max_length=4000)
    blocked_interventions: List[str] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    disclaimer: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Override the default disclaimer footer. "
                    "Leave unset to use the built-in MANO disclaimer.",
    )


class ClinicalPassportResponse(BaseModel):
    passport_id: str
    generated_at: datetime
    patient_id: str
    pdf_path: str = Field(..., description="Absolute path to the PDF on disk.")
    pdf_url: str = Field(..., description="Public URL for retrieving the PDF.")
    size_bytes: int = Field(..., ge=0)
    sections_included: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
