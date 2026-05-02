"""
Weather / weather-mood router (v2).

Two endpoints:

* ``POST /mood_correlation`` — Pearson correlations between recent mood/stress
  scores and aligned historical daily weather. Backed by Open-Meteo's free
  archive API.
* ``GET /forecast`` — current-day forecast + SAD-pathway composite for a
  named city. Thin wrapper over the legacy ``WeatherService`` with a v2
  source-tag envelope.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query

from lib.synthetic.weather_mood_service import (
    correlate_weather_mood,
    current_forecast,
)
from schemas.synthetic.weather_mood_schema import (
    FeatureCorrelation,
    ForecastResponse,
    WeatherMoodRequest,
    WeatherMoodResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_correlation_rows(rows) -> List[FeatureCorrelation]:
    return [FeatureCorrelation(**row) for row in (rows or [])]


@router.post("/mood_correlation", response_model=WeatherMoodResponse)
async def mood_correlation(request: WeatherMoodRequest) -> WeatherMoodResponse:
    """Correlate the patient's recent mood/stress scores against historical weather."""
    mood_dicts = [
        {
            "date": day.date,
            "mood_score": float(day.mood_score),
            "stress_score": float(day.stress_score) if day.stress_score is not None else None,
        }
        for day in request.mood_history
    ]

    result = await correlate_weather_mood(
        mood_history=mood_dicts,
        city=request.city,
        latitude=request.latitude,
        longitude=request.longitude,
    )

    return WeatherMoodResponse(
        city=result["city"],
        latitude=result["latitude"],
        longitude=result["longitude"],
        date_range=result["date_range"],
        n_samples=result["n_samples"],
        mood_correlations=_to_correlation_rows(result.get("mood_correlations")),
        stress_correlations=(
            _to_correlation_rows(result["stress_correlations"])
            if result.get("stress_correlations") is not None else None
        ),
        dominant_mood_driver=result.get("dominant_mood_driver"),
        dominant_stress_driver=result.get("dominant_stress_driver"),
        source=result["source"],
        notes=result.get("notes", []),
    )


@router.get("/forecast", response_model=ForecastResponse)
async def forecast(city: str = Query(..., min_length=2, max_length=80)) -> ForecastResponse:
    """Current-day weather + SAD composite for a named city."""
    try:
        payload = current_forecast(city)
    except Exception as exc:
        logger.exception("forecast_failed")
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {exc}") from exc
    return ForecastResponse(**payload)
