"""
Ambient sound router.

* ``POST /search`` — explicit mood search.
* ``POST /recommend`` — derive mood from a recent sentiment/emotion snapshot
  (used by the dashboard aggregator after a voice-journal submission).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.infra.event_bus import Topics, get_event_bus
from lib.synthetic.ambient_sound_service import (
    recommend_ambient,
    search_ambient,
)
from schemas.synthetic.ambient_sound_schema import (
    AmbientRecommendRequest,
    AmbientSearchRequest,
    AmbientSearchResponse,
    SoundMood,
    SoundTrack,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(payload: dict) -> AmbientSearchResponse:
    return AmbientSearchResponse(
        mood=SoundMood(payload["mood"]),
        tracks=[SoundTrack(**t) for t in payload.get("tracks", [])],
        source=payload["source"],
        provider=payload["provider"],
        cache_key=payload.get("cache_key"),
        notes=payload.get("notes", []),
    )


@router.post("/search", response_model=AmbientSearchResponse)
async def search(request: AmbientSearchRequest) -> AmbientSearchResponse:
    try:
        payload = await search_ambient(
            mood=request.mood.value,
            max_results=request.max_results,
            min_duration=request.min_duration,
            max_duration=request.max_duration,
            include_fallback=request.include_fallback,
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("ambient_search_failed")
        raise HTTPException(status_code=500, detail=f"Ambient search failed: {exc}") from exc

    try:
        await get_event_bus().publish(
            Topics.AMBIENT_SOUND_PROFILE,
            {
                "mood": request.mood.value,
                "source": payload["source"],
                "provider": payload["provider"],
                "result_count": len(payload.get("tracks", [])),
            },
        )
    except Exception:  # pragma: no cover — never block the response on bus errors
        pass

    return _to_response(payload)


@router.post("/recommend", response_model=AmbientSearchResponse)
async def recommend(request: AmbientRecommendRequest) -> AmbientSearchResponse:
    try:
        payload = await recommend_ambient(
            sentiment_score=request.sentiment_score,
            dominant_emotion=request.dominant_emotion,
            max_results=request.max_results,
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("ambient_recommend_failed")
        raise HTTPException(status_code=500, detail=f"Ambient recommend failed: {exc}") from exc
    return _to_response(payload)
