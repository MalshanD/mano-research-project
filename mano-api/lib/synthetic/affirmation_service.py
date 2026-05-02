"""
Daily Affirmation service.

Two free providers plus a curated fallback library:

1. **Affirmations.dev** — a public, rate-friendly endpoint that returns a
   single upbeat affirmation string. No key required.
2. **ZenQuotes** — returns a philosophical quote with attribution. No key
   required, but IP-bucketed rate limits apply (about 5 req/30s).
3. **Curated library** — a tone-grouped local list so the service *always*
   returns something, even offline. Hand-picked for mental-health context:
   nothing toxic-positive, nothing medicalising.

Tone selection
--------------
Callers can pass ``tone`` explicitly. If they don't, we derive it from the
current ``sentiment_score`` and ``trajectory_shape``, falling back to
``GENTLE`` when neither is available. This keeps a dashboard card useful
even when upstream analytics haven't run yet.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import AFFIRMATIONS_URL, ZENQUOTES_URL
from lib.infra.cache import get_cache
from lib.infra.security import sanitize_text

logger = logging.getLogger(__name__)


_TIMEOUT = 6.0
_CACHE_TTL_SECONDS = 6 * 3600
_NEGATIVE_CACHE_TTL = 15 * 60


# ─── Curated fallback library ─────────────────────────────────────────────
#
# Each entry is free of: toxic positivity, medical claims, comparison to
# others, and absolutes ("always", "never"). Each one is first-person and
# focused on the process of showing up.

_CURATED: Dict[str, List[str]] = {
    "gentle": [
        "Even small care, given today, counts.",
        "I can meet this moment without fixing all of it.",
        "Slow progress is still progress.",
        "It is okay to need rest today.",
        "I do not have to earn the right to be gentle with myself.",
    ],
    "energising": [
        "Today I get to try again, and trying is the work.",
        "One deliberate action compounds into momentum.",
        "My effort does not need to be perfect to be real.",
        "I am allowed to begin before I feel ready.",
        "The next small step is enough for now.",
    ],
    "grounding": [
        "I am here, in this body, in this room, in this breath.",
        "I can notice what I feel without becoming it.",
        "Five senses, one breath — I return.",
        "The ground is holding me. It has the whole time.",
        "My thoughts are weather, not climate.",
    ],
    "celebratory": [
        "Today I noticed something good — that noticing is a skill.",
        "A lighter day is still data. I can learn from it.",
        "I am allowed to take credit for quiet, ordinary wins.",
        "Momentum starts with a single kept promise to myself.",
        "The version of me that struggled last week deserves the thanks for this.",
    ],
}


# ─── Tone resolution ──────────────────────────────────────────────────────

def _derive_tone(
    sentiment_score: Optional[float],
    trajectory_shape: Optional[str],
) -> str:
    """Pure rule table — keeps recommendations deterministic + testable."""
    if trajectory_shape == "improving":
        return "celebratory"
    if trajectory_shape == "worsening":
        return "gentle"
    if trajectory_shape == "oscillating":
        return "grounding"

    if sentiment_score is not None:
        if sentiment_score >= 0.4:
            return "celebratory"
        if sentiment_score <= -0.4:
            return "gentle"
        if sentiment_score <= -0.1:
            return "grounding"
        if sentiment_score >= 0.1:
            return "energising"

    return "gentle"


# ─── Cache helper ─────────────────────────────────────────────────────────

def _cache_key(tone: str) -> str:
    # One bucket per (tone, calendar day) — a daily affirmation refreshes
    # at UTC midnight for the whole user base.
    today = date.today().isoformat()
    return (
        f"affirmation:v2:"
        f"{hashlib.sha256(f'{tone}|{today}'.encode('utf-8')).hexdigest()[:20]}"
    )


# ─── Provider calls ───────────────────────────────────────────────────────

async def _call_affirmations_dev(client: httpx.AsyncClient) -> Optional[str]:
    try:
        resp = await client.get(AFFIRMATIONS_URL, timeout=_TIMEOUT)
    except Exception as exc:
        logger.info("affirmations_dev_failed", extra={"error": str(exc)})
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    text = str(data.get("affirmation") or "").strip()
    return text or None


async def _call_zenquotes(client: httpx.AsyncClient) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = await client.get(ZENQUOTES_URL, timeout=_TIMEOUT)
    except Exception as exc:
        logger.info("zenquotes_failed", extra={"error": str(exc)})
        return None, None
    if resp.status_code != 200:
        return None, None
    try:
        data = resp.json()
    except Exception:
        return None, None
    if not isinstance(data, list) or not data:
        return None, None
    item = data[0] or {}
    text = str(item.get("q") or "").strip()
    author = (item.get("a") or None)
    if author:
        author = str(author).strip() or None
    return (text or None), author


# ─── Public API ───────────────────────────────────────────────────────────

async def get_daily_affirmation(
    *,
    tone: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    trajectory_shape: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Return a tone-appropriate affirmation with a source envelope.

    The function never raises — provider failure falls back to the curated
    library, which is guaranteed non-empty.
    """
    chosen_tone = (tone or _derive_tone(sentiment_score, trajectory_shape)).lower()
    if chosen_tone not in _CURATED:
        chosen_tone = "gentle"

    cache = get_cache()
    key = _cache_key(chosen_tone)

    if not force_refresh:
        try:
            hit = await cache.get(key)
        except Exception:  # pragma: no cover
            hit = None
        if hit:
            return {
                "text": hit.get("text", ""),
                "tone": chosen_tone,
                "author": hit.get("author"),
                "source": "cached",
                "provider": hit.get("provider", "curated"),
                "notes": hit.get("notes", []),
            }

    notes: List[str] = []

    # Tone-specific provider preference:
    # * Celebratory / energising → ZenQuotes reads better (authored quotes).
    # * Gentle / grounding → Affirmations.dev is first-person friendlier.
    primary = "zenquotes" if chosen_tone in ("celebratory", "energising") else "affirmations_dev"

    providers = (
        ("zenquotes", _call_zenquotes),
        ("affirmations_dev", _call_affirmations_dev),
    )
    if primary == "affirmations_dev":
        providers = (
            ("affirmations_dev", _call_affirmations_dev),
            ("zenquotes", _call_zenquotes),
        )

    start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        for name, call in providers:
            try:
                if name == "zenquotes":
                    text, author = await call(client)
                else:
                    text = await call(client)
                    author = None
            except Exception as exc:  # pragma: no cover
                notes.append(f"{name} error: {exc}")
                continue
            if text:
                safe_text = sanitize_text(text, max_length=400)
                latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "affirmation_generated",
                    extra={
                        "provider": name,
                        "tone": chosen_tone,
                        "latency_ms": round(latency_ms, 1),
                    },
                )
                try:
                    await cache.set(
                        key,
                        {"text": safe_text, "author": author, "provider": name, "notes": notes},
                        ttl=_CACHE_TTL_SECONDS,
                    )
                except Exception:  # pragma: no cover
                    pass
                return {
                    "text": safe_text,
                    "tone": chosen_tone,
                    "author": author,
                    "source": "live",
                    "provider": name,
                    "notes": notes,
                }
            notes.append(f"{name} empty")

    # Curated fallback — rotates by UTC date so a user sees the same quote
    # for a full day but a different one tomorrow.
    bucket = _CURATED[chosen_tone]
    daily_index = (date.today().toordinal()) % len(bucket)
    text = bucket[daily_index]
    notes.append("all providers unavailable — served curated library")
    try:
        await cache.set(
            key,
            {"text": text, "author": None, "provider": "curated", "notes": notes},
            ttl=_NEGATIVE_CACHE_TTL,
        )
    except Exception:  # pragma: no cover
        pass
    return {
        "text": text,
        "tone": chosen_tone,
        "author": None,
        "source": "fallback",
        "provider": "curated",
        "notes": notes,
    }


# Convenience sync helper for callers with only a tone in hand.
def pick_from_curated(tone: str) -> str:
    bucket = _CURATED.get(tone.lower(), _CURATED["gentle"])
    return random.choice(bucket)
