"""HTTP route layer for the consolidated Weather-Mood / SAD service.

The legacy ``/api/v1/weather/forecast`` and
``/api/v1/weather/mood_correlation`` routes (backed by two duplicated
services) are unchanged — these new endpoints sit at
``/api/v1/weather-v2`` and supersede them.

UI contract: every response carries ``severity_color``, ``icon_hint``,
``recommendation_id`` so the dashboard chip renders with no business
logic on the client.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from lib.synthetic import weather_v2_service
from schemas.synthetic.weather_v2_schema import (
    WeatherForecastResponse,
    WeatherMoodContext,
)

router = APIRouter()


@router.get(
    "/mood-context",
    response_model=WeatherMoodContext,
    summary="Today's weather + SAD risk + actionable recommendation",
    description=(
        "Resolves geolocation (caller-supplied → ip-api.com → Colombo "
        "fallback), fetches Open-Meteo, computes the SAD risk score "
        "with the evidence-based linear formula, and returns a "
        "ready-to-render payload with severity colour, icon, and a "
        "12-template recommendation."
    ),
)
async def mood_context(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
) -> WeatherMoodContext:
    return weather_v2_service.mood_context(lat=lat, lon=lon)


@router.get(
    "/forecast-risk",
    response_model=WeatherForecastResponse,
    summary="7-day SAD-risk forecast aligned with the Seq2Seq window",
    description=(
        "Per-day SAD risk score + recommendation + UI render hints over "
        "the next ``horizon_days`` (max 7). Pairs naturally with the "
        "rehearsal engine's weekly chunks."
    ),
)
async def forecast_risk(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    horizon_days: int = Query(7, ge=1, le=7),
) -> WeatherForecastResponse:
    return weather_v2_service.forecast_risk(lat=lat, lon=lon, horizon_days=horizon_days)
