"""
Pydantic schemas for the consolidated Weather-Mood / SAD service.

Replaces the duplicate ``weather_service`` + ``weather_mood_service``
pair flagged in the audit. Single source of truth for everything the
UI shows on the Today's Weather card and the Mood Forecast widget.

API: Open-Meteo (no key, no rate limit) + ip-api.com fallback for
geolocation. Hard fallback to Colombo, Sri Lanka coordinates so the
endpoint never returns 5xx for missing geolocation.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WeatherSnapshot(BaseModel):
    """One day's weather signal — flat shape so the UI binds easily."""

    uv_index: Optional[float] = None
    sunshine_hours: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    wind_speed_kmh: Optional[float] = None


class WeatherDayForecast(BaseModel):
    day_offset: int
    sad_risk_score: float = Field(..., ge=0.0, le=1.0)
    weather: WeatherSnapshot
    summary: str
    severity_color: str
    icon_hint: str


class MoodModifier(BaseModel):
    """Per-channel weather → mood multipliers for downstream consumers
    (the dashboard intelligence layer + the rehearsal engine).
    """

    energy: float
    motivation: float
    sociability: float


class WeatherMoodContext(BaseModel):
    """Today's context — the payload the My Summary card binds to."""

    location: str = Field(
        ..., description="'Auto-detected via IP' | 'Colombo, Sri Lanka' | "
                         "'Custom (lat, lon)'.",
    )
    latitude: float
    longitude: float
    geocoding_source: str = Field(
        ...,
        description="'caller_supplied' | 'ip_api' | 'fallback_colombo'",
    )

    weather: WeatherSnapshot
    sad_risk_score: float = Field(..., ge=0.0, le=1.0)
    sad_severity_label: str = Field(
        ...,
        description="'low' | 'moderate' | 'elevated' | 'high'",
    )
    severity_color: str
    icon_hint: str
    mood_modifier: MoodModifier
    recommendation: str
    recommendation_id: str = Field(
        ...,
        description="Stable identifier for the recommendation card "
                    "(useful for analytics + UI animation keys).",
    )
    computed_at: datetime
    source: str = "live"


class WeatherForecastResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    days: List[WeatherDayForecast]
    horizon_days: int
    computed_at: datetime
    source: str = "live"
