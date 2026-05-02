"""
Pydantic schemas for the Future-Self Narrative Engine.

Takes a Seq2Seq projection and emits a 3-4 sentence first-person
narrative as if the patient were speaking on Day 7 of the projected
plan. Groq Llama 3.1 8B when available; deterministic templates when
not.

The narrative MUST never reveal AI/model origin (that's a guideline
invariant — see ``_PROHIBITED`` in the service). The endpoint runs a
post-processing regex strip and falls back to template if the LLM
output trips it.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    RiskLevel,
)


class PatientNarrativeContext(BaseModel):
    """Compact context window passed to the narrative engine.

    The engine doesn't need a full PatientState — only the projection,
    a handful of demographic hints, and the intervention being
    rehearsed.
    """

    age_group: Optional[str] = Field(
        None,
        description="Free-text age band, e.g. '25-34'. Used for tone, "
                    "not for any inference. Optional.",
    )
    risk_level: Optional[RiskLevel] = None
    primary_concern: Optional[str] = Field(
        None, max_length=80,
        description="One-word/short-phrase concern, e.g. 'sleep', "
                    "'stress', 'anxiety'. Used for theme selection.",
    )
    intervention_type: Optional[InterventionType] = None


class FutureSelfRequest(BaseModel):
    projection: List[DayVitals] = Field(
        ..., min_length=1, max_length=14,
        description="Seq2Seq output — 1 row per day. Day 0 first.",
    )
    context: PatientNarrativeContext = Field(default_factory=PatientNarrativeContext)


class FutureSelfNarrative(BaseModel):
    narrative: str
    source: str = Field(
        ..., description="'groq' | 'template' — provenance for QA."
    )
    sentence_count: int
    contains_signal_reference: bool = Field(
        ...,
        description="True iff the narrative cites a specific vital "
                    "improvement (sleep_avg, stress, etc.). Frontend "
                    "uses this to optionally show the source data card.",
    )


class ParallelFuturesRequest(BaseModel):
    projections: List[List[DayVitals]] = Field(
        ..., min_length=2, max_length=3,
        description="Two or three Seq2Seq projections to compare. The "
                    "engine batches them into a single Groq call so we "
                    "stay within the free-tier RPM budget.",
    )
    scenario_names: List[str] = Field(
        ..., min_length=2, max_length=3,
        description="One label per projection ('CBT', 'Exercise', "
                    "'Continue current plan'). Echoed back on each item.",
    )
    context: PatientNarrativeContext = Field(default_factory=PatientNarrativeContext)


class ScenarioNarrative(BaseModel):
    scenario_name: str
    narrative: str


class ParallelFuturesResponse(BaseModel):
    items: List[ScenarioNarrative]
    source: str
