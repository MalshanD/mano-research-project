"""
Schemas for the Daily Affirmation service.

The service stitches two free APIs (ZenQuotes, Affirmations.dev) with a
curated fallback. Callers typically hit ``GET /daily`` once per session and
render the result as a header card.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AffirmationTone(str, Enum):
    GENTLE = "gentle"          # e.g. after a hard day
    ENERGISING = "energising"  # e.g. before a deliberate practice
    GROUNDING = "grounding"    # e.g. anxious / scattered
    CELEBRATORY = "celebratory"  # e.g. trajectory improving


class AffirmationRequest(BaseModel):
    tone: Optional[AffirmationTone] = Field(
        default=None,
        description="Optional tone — if omitted, a tone is picked from the patient context.",
    )
    sentiment_score: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0,
        description=(
            "Recent sentiment compound (−1..+1). Used to auto-pick a tone "
            "when ``tone`` is not supplied."
        ),
    )
    trajectory_shape: Optional[
        Literal["improving", "worsening", "stable", "oscillating"]
    ] = None
    force_refresh: bool = Field(
        default=False,
        description="Skip the 6h cache and re-fetch. Useful for QA.",
    )


class AffirmationResponse(BaseModel):
    text: str
    tone: AffirmationTone
    author: Optional[str] = Field(
        default=None,
        description="Attribution when available (ZenQuotes returns an author).",
    )
    source: Literal["live", "cached", "fallback"]
    provider: Literal["zenquotes", "affirmations_dev", "curated"]
    notes: List[str] = Field(default_factory=list)
