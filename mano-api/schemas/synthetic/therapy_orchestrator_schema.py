"""
Schemas for the Care-Path Therapy Orchestrator.

Context vs. the existing in-session chat service
------------------------------------------------
``lib/therapy/therapy_service.py`` is a per-conversation state machine —
check_in → listening → cbt_check → reframe → intervention → wind_down →
summary. It lives for the duration of one chat.

This orchestrator is a *longitudinal* care-path state machine. It tracks a
patient across weeks and publishes phase transitions that other subsystems
(dashboard aggregator, PPO reranker, clinical passport) consume. The two
machines never collide: the chat service drives one conversation, the
orchestrator drives the overall care journey.

Care phases
-----------
* **intake** — onboarding, first assessment, baseline vitals, consent.
* **stabilise** — acute symptom reduction. Short review cadence, safety-
  first interventions, conservative intensity.
* **practice** — skill-building. New interventions can be tried; adherence
  tracking becomes central.
* **integrate** — skills become routine. Intensity can ease; focus shifts
  to generalisation across life domains.
* **maintain** — long-term wellness check-ins. Phase may oscillate back to
  stabilise on deterioration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CarePhase(str, Enum):
    INTAKE = "intake"
    STABILISE = "stabilise"
    PRACTICE = "practice"
    INTEGRATE = "integrate"
    MAINTAIN = "maintain"


class PhaseTrigger(str, Enum):
    """Inputs that can drive a phase transition."""
    ONBOARDING_COMPLETE = "onboarding_complete"
    RISK_IMPROVED = "risk_improved"
    RISK_DETERIORATED = "risk_deteriorated"
    SKILL_PRACTISED = "skill_practised"            # e.g. 5+ journal entries
    ADHERENCE_HIGH = "adherence_high"              # ≥80% intervention completion
    ADHERENCE_LOW = "adherence_low"                # ≤40% completion
    CRISIS_FLAG = "crisis_flag"                    # voice-journal crisis signal
    TIME_ELAPSED = "time_elapsed"                  # scheduled review cadence
    CLINICIAN_OVERRIDE = "clinician_override"      # explicit manual transition


class CarePathSnapshot(BaseModel):
    """Point-in-time inputs for the state machine.

    Every field is optional so callers can forward whatever signals are
    available. Missing signals simply don't drive transitions.
    """
    patient_id: str = Field(..., min_length=1, max_length=64)
    current_risk_level: Optional[Literal["low", "medium", "high"]] = None
    mean_high_risk_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    trajectory_shape: Optional[
        Literal["improving", "worsening", "stable", "oscillating"]
    ] = None
    adherence_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Fraction of recommended interventions completed in the last 14d.",
    )
    journal_entries_14d: Optional[int] = Field(default=None, ge=0)
    crisis_language_detected: bool = False
    days_since_intake: Optional[int] = Field(default=None, ge=0)
    clinician_override: Optional[CarePhase] = None


class CarePathState(BaseModel):
    """Persisted state — one row per patient."""
    patient_id: str
    phase: CarePhase
    phase_started_at: datetime
    updated_at: datetime
    history: List["PhaseTransition"] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class PhaseTransition(BaseModel):
    from_phase: Optional[CarePhase] = None
    to_phase: CarePhase
    trigger: PhaseTrigger
    at: datetime
    rationale: str


# Forward-reference resolution
CarePathState.model_rebuild()


class PhaseTransitionRequest(BaseModel):
    snapshot: CarePathSnapshot


class PhaseTransitionResponse(BaseModel):
    state: CarePathState
    transitioned: bool
    phase_guidance: str = Field(
        ...,
        description="Short, plain-language description of what this phase means "
                    "for the patient's care plan.",
    )
    recommended_intervention_tones: List[str] = Field(
        default_factory=list,
        description="Ranked intervention categories the reranker should prefer "
                    "while the patient is in this phase.",
    )
    review_cadence_days: int = Field(
        ..., ge=1, le=90,
        description="How often the orchestrator wants a fresh snapshot.",
    )
    safety_escalation_required: bool = False
