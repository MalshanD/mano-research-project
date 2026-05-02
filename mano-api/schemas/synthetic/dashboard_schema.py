"""
Dashboard intelligence — aggregator schemas.

The aggregator merges the results of several Phase 1 / 2 / 3 services into
one payload so the dashboard only has to fire a single HTTP call on load.
Partial failures are first-class: each panel carries its own ``source`` tag
so the frontend can render a graceful degraded state per panel.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.affirmation_schema import AffirmationResponse
from schemas.synthetic.ambient_sound_schema import AmbientSearchResponse
from schemas.synthetic.evidence_schema import EvidenceResponse
from schemas.synthetic.narrative_schema import (
    NarrativeLength,
    NarrativeResponse,
    NarrativeTone,
    TrajectorySummary,
)
from schemas.synthetic.weather_mood_schema import ForecastResponse


class PanelStatus(BaseModel):
    """Per-panel health envelope — always present even when the panel loaded."""
    name: str
    status: Literal["ok", "degraded", "error"]
    source: Optional[str] = Field(
        default=None, description="live | cached | fallback | mixed"
    )
    provider: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class DashboardRequest(BaseModel):
    """What the dashboard needs to show.

    Every field is optional — when a field is omitted the corresponding
    panel is simply left out of the response. This keeps the aggregator
    useful on very first login (patient has no trajectory yet) and on
    returning visits (patient has everything).
    """

    # Narrative panel — derived from a trajectory summary.
    trajectory: Optional[TrajectorySummary] = None
    narrative_tone: NarrativeTone = NarrativeTone.HOPEFUL
    narrative_length: NarrativeLength = NarrativeLength.SHORT
    patient_voice: Optional[str] = Field(default=None, max_length=500)

    # Evidence panel — picks the intervention from the trajectory if present.
    evidence_intervention: Optional[str] = Field(default=None, max_length=60)
    evidence_max_cards: int = Field(default=3, ge=1, le=6)

    # Weather panel.
    city: Optional[str] = Field(default=None, min_length=2, max_length=80)

    # Affirmation panel.
    sentiment_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0)

    # Ambient panel — opt-in; typically follows a recent voice-journal submit.
    include_ambient: bool = True
    dominant_emotion: Optional[str] = Field(default=None, max_length=40)
    ambient_max_results: int = Field(default=3, ge=1, le=8)


class DashboardResponse(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_hit: bool = False

    narrative: Optional[NarrativeResponse] = None
    evidence: Optional[EvidenceResponse] = None
    weather_forecast: Optional[ForecastResponse] = None
    affirmation: Optional[AffirmationResponse] = None
    ambient: Optional[AmbientSearchResponse] = None

    panels: List[PanelStatus] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
