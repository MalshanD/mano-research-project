"""
Enhanced Dashboard API — Mood-Aware Content

New endpoints (additive — no changes to existing routes):
  /api/v1/dashboard/content       — Affirmation + quote + suggested action
  /api/v1/dashboard/mood-trend    — Journal-based mood trajectory
  /api/v1/dashboard/journal-sentiment — Analyze a journal entry's sentiment
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from db.database import get_db
from lib.wellness.affirmation_service import affirmation_service, journal_sentiment

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard Enhancement"])


class JournalEntryInput(BaseModel):
    text: str


class JournalBatchInput(BaseModel):
    entries: List[dict]  # [{text, created_at}, ...]


@router.get(
    "/content",
    summary="Get mood-aware dashboard content",
    description=(
        "Returns a daily affirmation (Affirmations.dev, unlimited) and "
        "a motivational quote (ZenQuotes, 5 req/30s). Both APIs are free "
        "with no key required. Local fallbacks ensure the endpoint never fails."
    ),
)
async def get_dashboard_content():
    try:
        content = await affirmation_service.get_dashboard_content()
        return content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard content error: {str(e)}",
        )


@router.post(
    "/journal-sentiment",
    summary="Analyze journal entry sentiment (VADER, local, unlimited)",
    description=(
        "Runs VADER sentiment analysis on a journal entry text. "
        "Returns mood score (1-10), label, and polarity breakdown. "
        "Pure local computation — no API calls, no rate limits."
    ),
)
async def analyze_journal_sentiment(entry: JournalEntryInput):
    if not entry.text.strip():
        raise HTTPException(status_code=400, detail="Journal text cannot be empty")
    result = journal_sentiment.analyze_entry(entry.text)
    return result


@router.post(
    "/mood-trend",
    summary="Calculate mood trend from journal history",
    description=(
        "Analyzes multiple journal entries to compute a mood trajectory. "
        "Returns trend direction (improving/declining/stable), average mood, "
        "and change magnitude. Used for the Dashboard mood chart."
    ),
)
async def get_mood_trend(batch: JournalBatchInput):
    if not batch.entries:
        return {"trend": "stable", "avg_mood": 5.0, "change": 0.0, "data_points": 0}
    trend = journal_sentiment.get_mood_trend(batch.entries)
    return trend
