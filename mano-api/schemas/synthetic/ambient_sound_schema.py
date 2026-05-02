"""
Schemas for the Ambient Sound library.

The library surfaces short, loopable soundscapes mapped to psychological
goals (calm, focus, sleep, uplift, ground). Each sound carries provenance
and a licence string so the frontend can render attribution when required.

Request-side schemas are deliberately small — callers typically supply only
a ``mood`` tag, and the service handles curated-fallback vs live Freesound
search internally.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SoundMood(str, Enum):
    CALM = "calm"
    FOCUS = "focus"
    SLEEP = "sleep"
    UPLIFT = "uplift"
    GROUND = "ground"


class SoundTrack(BaseModel):
    """One playable soundscape item."""
    id: str = Field(..., description="Stable identifier (freesound:<num> or curated:<slug>).")
    title: str
    mood: SoundMood
    description: Optional[str] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0.0)
    preview_url: str = Field(..., description="Direct URL to an MP3/OGG preview.")
    page_url: Optional[str] = Field(
        default=None,
        description="Source page (Freesound, Pixabay etc.) for attribution clicks.",
    )
    provider: Literal["freesound", "curated"]
    licence: str = Field(..., description="License tag (e.g. 'CC0', 'CC-BY', 'Pixabay').")
    attribution: Optional[str] = Field(
        default=None,
        description="Pre-formatted attribution string when the licence requires it.",
    )
    tags: List[str] = Field(default_factory=list)


class AmbientSearchRequest(BaseModel):
    mood: SoundMood = Field(..., description="Target psychological mood.")
    max_results: int = Field(default=5, ge=1, le=20)
    min_duration: Optional[float] = Field(
        default=None, ge=0.0,
        description="Filter results shorter than this many seconds.",
    )
    max_duration: Optional[float] = Field(
        default=None, ge=0.0,
        description="Filter results longer than this many seconds.",
    )
    include_fallback: bool = Field(
        default=True,
        description=(
            "If the Freesound call fails or returns too few results, top up "
            "from the curated fallback library."
        ),
    )


class AmbientSearchResponse(BaseModel):
    mood: SoundMood
    tracks: List[SoundTrack]
    source: Literal["live", "cached", "fallback", "mixed"]
    provider: Literal["freesound", "curated", "mixed"]
    cache_key: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class AmbientRecommendRequest(BaseModel):
    """Maps a sentiment/emotion snapshot → a suggested mood + tracks.

    Typically consumed by the dashboard aggregator after a voice-journal
    submission so the UI can auto-suggest a matching soundscape.
    """
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    dominant_emotion: Optional[str] = Field(default=None, max_length=40)
    max_results: int = Field(default=4, ge=1, le=12)
