"""
Affirmation router.

* ``POST /daily`` — body-driven request (tone / sentiment / trajectory).
* ``GET /daily`` — convenience GET for dashboard poll flows; query-string
  driven.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from lib.synthetic.affirmation_service import get_daily_affirmation
from schemas.synthetic.affirmation_schema import (
    AffirmationRequest,
    AffirmationResponse,
    AffirmationTone,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(payload: dict) -> AffirmationResponse:
    return AffirmationResponse(
        text=payload["text"],
        tone=AffirmationTone(payload["tone"]),
        author=payload.get("author"),
        source=payload["source"],
        provider=payload["provider"],
        notes=payload.get("notes", []),
    )


@router.post("/daily", response_model=AffirmationResponse)
async def daily_post(request: AffirmationRequest) -> AffirmationResponse:
    try:
        payload = await get_daily_affirmation(
            tone=request.tone.value if request.tone else None,
            sentiment_score=request.sentiment_score,
            trajectory_shape=request.trajectory_shape,
            force_refresh=request.force_refresh,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("affirmation_failed")
        raise HTTPException(status_code=500, detail=f"Affirmation failed: {exc}") from exc
    return _to_response(payload)


@router.get("/daily", response_model=AffirmationResponse)
async def daily_get(
    tone: Optional[AffirmationTone] = Query(default=None),
    sentiment_score: Optional[float] = Query(default=None, ge=-1.0, le=1.0),
    trajectory_shape: Optional[
        Literal["improving", "worsening", "stable", "oscillating"]
    ] = Query(default=None),
    force_refresh: bool = Query(default=False),
) -> AffirmationResponse:
    try:
        payload = await get_daily_affirmation(
            tone=tone.value if tone else None,
            sentiment_score=sentiment_score,
            trajectory_shape=trajectory_shape,
            force_refresh=force_refresh,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("affirmation_failed")
        raise HTTPException(status_code=500, detail=f"Affirmation failed: {exc}") from exc
    return _to_response(payload)
