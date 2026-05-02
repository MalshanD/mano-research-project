"""
Schemas for the weather-mood correlation service.

The patient supplies their recent daily mood/stress scores; we fetch the
matching historical daily weather from Open-Meteo and return Pearson
correlations per weather feature, plus qualitative interpretations.

This is an analytics tool, not a clinical decision aid. Correlations from a
single patient over a short window are inherently noisy; the service surfaces
``n_samples`` and a ``strength`` label so the UI never overstates the finding.
"""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MoodDay(BaseModel):
    date: date
    mood_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Self-reported mood, 0 (very low) — 1 (very high).",
    )
    stress_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Optional self-reported stress, 0 — 1.",
    )


class WeatherMoodRequest(BaseModel):
    city: Optional[str] = Field(
        default=None,
        description="Named city. Geocoded if not in the curated list.",
    )
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    mood_history: List[MoodDay] = Field(
        ...,
        min_length=5,
        max_length=90,
        description=(
            "Recent daily mood scores (≥5 days). Must cover a contiguous date "
            "range; missing days are tolerated but reduce the sample size."
        ),
    )


class FeatureCorrelation(BaseModel):
    feature: str = Field(..., description="Weather feature name, e.g. 'uv_index_max'.")
    pearson_r: float = Field(..., ge=-1.0, le=1.0)
    n_samples: int
    strength: Literal["strong", "moderate", "weak", "negligible"]
    direction: Literal["positive", "negative", "none"]
    interpretation: str


class WeatherMoodResponse(BaseModel):
    city: str
    latitude: float
    longitude: float
    date_range: str = Field(..., description="Earliest → latest date aligned.")
    n_samples: int

    mood_correlations: List[FeatureCorrelation]
    stress_correlations: Optional[List[FeatureCorrelation]] = None

    dominant_mood_driver: Optional[str] = None
    dominant_stress_driver: Optional[str] = None

    source: str = Field(..., description="live | cached | fallback")
    provider: str = "open-meteo-archive"
    notes: List[str] = Field(default_factory=list)


class ForecastRequest(BaseModel):
    city: str = Field(..., min_length=2, max_length=80)


class ForecastResponse(BaseModel):
    city: str
    latitude: float
    longitude: float
    temperature_max_c: float
    temperature_min_c: float
    uv_index_max: float
    sunshine_hours: float
    daylight_hours: float
    humidity_pct: float
    precipitation_hours: float
    wind_speed_max_kmh: float
    sad_composite: float = Field(
        ..., ge=0.0, le=1.0,
        description="Composite SAD intensity [0..1] from the 3-pathway model.",
    )
    source: str
    provider: str = "open-meteo"
    notes: List[str] = Field(default_factory=list)
