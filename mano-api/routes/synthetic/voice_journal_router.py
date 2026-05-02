"""
Voice Journal router.

Two endpoints:

* ``POST /ingest`` — transcribe (if needed) + analyse + return structured
  response with the source-tag envelope.
* ``POST /trend`` — pure aggregator over a caller-supplied history window.
  Kept in this router so the dashboard can compute trend cards without a
  separate service call.

The router is intentionally stateless — persistence of journal entries is the
caller's responsibility (Component 2 stores them against the patient's
record). Keeping the router stateless means the analytics pipeline can be
unit-tested without DB coupling.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException

from lib.infra.event_bus import Topics, get_event_bus
from lib.synthetic.voice_journal_service import (
    analyse_voice_journal,
    summarise_trend,
)
from schemas.synthetic.voice_journal_schema import (
    EmotionSummary,
    ThemeKeyword,
    VoiceJournalRequest,
    VoiceJournalResponse,
    VoiceJournalTrendResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=VoiceJournalResponse)
async def ingest(request: VoiceJournalRequest) -> VoiceJournalResponse:
    """Analyse a single voice-journal submission."""
    try:
        result = await analyse_voice_journal(request)
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("voice_journal_failed")
        raise HTTPException(status_code=500, detail=f"Voice journal analysis failed: {exc}") from exc

    # Fire-and-forget event so downstream components (dashboard aggregator,
    # therapy orchestrator) can react without polling.
    try:
        bus = get_event_bus()
        await bus.publish(
            Topics.VOICE_JOURNAL_PROCESSED,
            {
                "word_count": result.word_count,
                "sentiment_label": result.sentiment_label,
                "dominant_emotion": result.dominant_emotion,
                "crisis_language_detected": result.crisis_language_detected,
                "transcription_source": result.transcription_source,
            },
        )
    except Exception as exc:  # pragma: no cover — event bus never blocks the response
        logger.info("voice_journal_event_publish_failed", extra={"error": str(exc)})

    return result


@router.post("/trend", response_model=VoiceJournalTrendResponse)
async def trend(
    history: List[Dict[str, Any]] = Body(
        ...,
        description=(
            "Ordered list of previously-analysed VoiceJournalResponse dicts "
            "(oldest first). Must contain at least one row; 4+ rows are "
            "required before a sentiment trend direction is computed."
        ),
    ),
    top_k: int = Body(default=5, ge=1, le=10),
) -> VoiceJournalTrendResponse:
    if not history:
        raise HTTPException(status_code=400, detail="history must contain at least one row")

    summary = summarise_trend(history, top_k=top_k)
    return VoiceJournalTrendResponse(
        samples=summary["samples"],
        mean_sentiment=summary["mean_sentiment"],
        sentiment_trend=summary["sentiment_trend"],
        top_emotions=[EmotionSummary(**row) for row in summary["top_emotions"]],
        top_themes=[ThemeKeyword(**row) for row in summary["top_themes"]],
        window_start=summary["window_start"],
        window_end=summary["window_end"],
        notes=summary["notes"],
    )
