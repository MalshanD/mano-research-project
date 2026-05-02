"""
Ambient Sound library service.

Strategy
--------
* **Primary** — Freesound API (`text search` endpoint) with a mood →
  query-term map. Results are cached for 12 h because soundscapes don't
  churn and Freesound's free tier has an hourly quota we respect.
* **Fallback** — a curated list of CC0 / Pixabay-style tracks baked into the
  module. The fallback guarantees the UI never renders an empty library even
  when the key is unset, the network is down, or Freesound is rate-limiting.
* The response carries a ``source`` envelope so the frontend can label
  results live / cached / fallback / mixed.

Why not store the full audio locally? Two reasons: (1) we want permissive
licences and fresh inventory without bundling large binary assets into the
repo, and (2) the free Freesound previews are already hosted on a CDN we
can link straight from the browser. The service therefore only ships
metadata + URLs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import FREESOUND_BASE_URL, settings
from lib.infra.cache import get_cache

logger = logging.getLogger(__name__)


# ─── Tuning ────────────────────────────────────────────────────────────────

_SEARCH_TIMEOUT = 6.0
_CACHE_TTL_SECONDS = 12 * 3600
_NEGATIVE_CACHE_TTL = 30 * 60

# Mood → Freesound query term(s). Chosen to return loop-friendly ambient
# textures; the curated fallback mirrors the same buckets.
_MOOD_QUERIES: Dict[str, List[str]] = {
    "calm": ["soft ambient pad", "gentle rain loop", "warm drone ambient"],
    "focus": ["lofi study loop", "brown noise steady", "minimalist ambient focus"],
    "sleep": ["slow delta drone", "night rain loop", "deep sleep pad"],
    "uplift": ["morning birdsong", "soft piano ambient warm", "bright pad loop"],
    "ground": ["forest ambience", "ocean waves loop", "grounded nature ambience"],
}


# ─── Curated fallback library ──────────────────────────────────────────────
#
# All URLs are stable Pixabay / freesound CC0 previews. We embed the
# provider/licence so attribution renders identically to live results.

_CURATED_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "calm": [
        {
            "id": "curated:calm-01",
            "title": "Soft Rain on a Window",
            "description": "Gentle, steady rainfall with no thunder.",
            "duration_seconds": 600.0,
            "preview_url": "https://cdn.pixabay.com/audio/2022/03/15/audio_11b7b04e67.mp3",
            "page_url": "https://pixabay.com/sound-effects/soft-rain-ambient-111154/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay (free for commercial use).",
            "tags": ["rain", "ambient", "calm"],
        },
        {
            "id": "curated:calm-02",
            "title": "Warm Ambient Pad",
            "description": "Slow-evolving low synth pad, sub-audible bass.",
            "duration_seconds": 540.0,
            "preview_url": "https://cdn.pixabay.com/audio/2023/04/17/audio_b2c0e91a5a.mp3",
            "page_url": "https://pixabay.com/music/ambient-warm-ambient-pad-149028/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["pad", "ambient", "calm"],
        },
    ],
    "focus": [
        {
            "id": "curated:focus-01",
            "title": "Brown Noise",
            "description": "Steady brown-noise bed — good for concentration.",
            "duration_seconds": 1800.0,
            "preview_url": "https://cdn.pixabay.com/audio/2022/10/25/audio_ad15af8a6d.mp3",
            "page_url": "https://pixabay.com/sound-effects/brown-noise-ambient-124867/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["brown-noise", "focus"],
        },
        {
            "id": "curated:focus-02",
            "title": "Lo-Fi Study Loop",
            "description": "Slow, unobtrusive lo-fi beat.",
            "duration_seconds": 300.0,
            "preview_url": "https://cdn.pixabay.com/audio/2023/06/21/audio_4f4e5ab9c6.mp3",
            "page_url": "https://pixabay.com/music/beats-lofi-study-158351/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["lofi", "focus"],
        },
    ],
    "sleep": [
        {
            "id": "curated:sleep-01",
            "title": "Night Rain Loop",
            "description": "Soft night rain with distant thunder dropped out.",
            "duration_seconds": 900.0,
            "preview_url": "https://cdn.pixabay.com/audio/2022/11/23/audio_c0b5b58b3e.mp3",
            "page_url": "https://pixabay.com/sound-effects/night-rain-ambient-130045/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["rain", "night", "sleep"],
        },
        {
            "id": "curated:sleep-02",
            "title": "Slow Delta Drone",
            "description": "Very slow evolving drone — helpful for drifting off.",
            "duration_seconds": 1200.0,
            "preview_url": "https://cdn.pixabay.com/audio/2023/01/09/audio_b03e7a5f34.mp3",
            "page_url": "https://pixabay.com/music/ambient-delta-drone-142093/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["drone", "sleep"],
        },
    ],
    "uplift": [
        {
            "id": "curated:uplift-01",
            "title": "Morning Birdsong",
            "description": "Dawn chorus in a temperate forest.",
            "duration_seconds": 480.0,
            "preview_url": "https://cdn.pixabay.com/audio/2022/05/12/audio_5a7a8d65a1.mp3",
            "page_url": "https://pixabay.com/sound-effects/birds-morning-ambient-115112/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["birds", "morning", "uplift"],
        },
        {
            "id": "curated:uplift-02",
            "title": "Warm Piano Ambience",
            "description": "Soft piano chords with natural reverb.",
            "duration_seconds": 360.0,
            "preview_url": "https://cdn.pixabay.com/audio/2023/08/05/audio_d58b7e2a0f.mp3",
            "page_url": "https://pixabay.com/music/ambient-warm-piano-162731/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["piano", "ambient", "uplift"],
        },
    ],
    "ground": [
        {
            "id": "curated:ground-01",
            "title": "Forest Ambience",
            "description": "Mid-morning forest with wind through leaves.",
            "duration_seconds": 720.0,
            "preview_url": "https://cdn.pixabay.com/audio/2022/04/20/audio_3e8b1e7b2a.mp3",
            "page_url": "https://pixabay.com/sound-effects/forest-ambient-112920/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["forest", "nature", "ground"],
        },
        {
            "id": "curated:ground-02",
            "title": "Ocean Waves",
            "description": "Small-to-medium waves on a sandy shore.",
            "duration_seconds": 900.0,
            "preview_url": "https://cdn.pixabay.com/audio/2023/02/11/audio_0f9c2e7c0b.mp3",
            "page_url": "https://pixabay.com/sound-effects/ocean-waves-ambient-144320/",
            "provider": "curated",
            "licence": "Pixabay",
            "attribution": "Sound via Pixabay.",
            "tags": ["ocean", "waves", "ground"],
        },
    ],
}


# ─── Cache helper ──────────────────────────────────────────────────────────

def _cache_key(mood: str, max_results: int) -> str:
    blob = f"{mood}|{max_results}".encode("utf-8")
    return f"ambient:v2:{hashlib.sha256(blob).hexdigest()[:20]}"


# ─── Freesound wrapper ─────────────────────────────────────────────────────

async def _freesound_search(
    client: httpx.AsyncClient, query: str, page_size: int,
) -> List[Dict[str, Any]]:
    """Query Freesound's text-search endpoint. Returns a list of track dicts
    in the shape of ``SoundTrack`` (minus the mood label).

    Silently returns ``[]`` on any error — the caller decides how to handle
    an empty live result.
    """
    if not settings.freesound_api_key:
        return []
    params = {
        "query": query,
        "page_size": page_size,
        "fields": "id,name,description,duration,previews,url,license,tags",
        "filter": "duration:[60 TO 1800]",   # Only loop-worthy durations.
        "sort": "score",
        "token": settings.freesound_api_key,
    }
    try:
        resp = await client.get(
            f"{FREESOUND_BASE_URL}/search/text/",
            params=params, timeout=_SEARCH_TIMEOUT,
        )
    except Exception as exc:
        logger.info("freesound_failed", extra={"error": str(exc)})
        return []
    if resp.status_code != 200:
        logger.info("freesound_non_200", extra={"status": resp.status_code})
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    results = data.get("results") or []
    out: List[Dict[str, Any]] = []
    for item in results:
        preview_url = ((item.get("previews") or {}).get("preview-lq-mp3")
                       or (item.get("previews") or {}).get("preview-hq-mp3"))
        if not preview_url:
            continue
        licence = str(item.get("license") or "").strip() or "Unspecified"
        tags = [str(t) for t in (item.get("tags") or [])][:8]
        out.append({
            "id": f"freesound:{item.get('id')}",
            "title": str(item.get("name") or "Untitled").strip(),
            "description": (item.get("description") or "")[:280] or None,
            "duration_seconds": float(item.get("duration") or 0.0) or None,
            "preview_url": preview_url,
            "page_url": str(item.get("url") or "") or None,
            "provider": "freesound",
            "licence": licence,
            "attribution": (
                f"Freesound — {licence}" if licence != "Unspecified" else None
            ),
            "tags": tags,
        })
    return out


# ─── Public API ───────────────────────────────────────────────────────────

def _curated_for_mood(mood: str, count: int) -> List[Dict[str, Any]]:
    rows = _CURATED_LIBRARY.get(mood, [])
    # Copy so callers can mutate mood without affecting the frozen library.
    return [dict(r, mood=mood) for r in rows[:count]]


def _filter_duration(
    tracks: List[Dict[str, Any]], min_d: Optional[float], max_d: Optional[float],
) -> List[Dict[str, Any]]:
    if not (min_d or max_d):
        return tracks
    kept: List[Dict[str, Any]] = []
    for t in tracks:
        dur = t.get("duration_seconds")
        if dur is None:
            kept.append(t)
            continue
        if min_d is not None and dur < min_d:
            continue
        if max_d is not None and dur > max_d:
            continue
        kept.append(t)
    return kept


async def search_ambient(
    *,
    mood: str,
    max_results: int = 5,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
    include_fallback: bool = True,
) -> Dict[str, Any]:
    """Return a source-tagged payload of tracks for a given mood."""
    mood = (mood or "").strip().lower()
    if mood not in _MOOD_QUERIES:
        return {
            "mood": mood,
            "tracks": [],
            "source": "fallback",
            "provider": "curated",
            "cache_key": None,
            "notes": [f"unknown mood '{mood}'"],
        }

    cache = get_cache()
    key = _cache_key(mood, max_results)
    try:
        hit = await cache.get(key)
    except Exception:  # pragma: no cover
        hit = None
    if hit:
        tracks = _filter_duration(hit.get("tracks", []), min_duration, max_duration)
        return {
            "mood": mood,
            "tracks": [dict(t, mood=mood) for t in tracks[:max_results]],
            "source": "cached",
            "provider": hit.get("provider", "freesound"),
            "cache_key": key,
            "notes": hit.get("notes", []),
        }

    notes: List[str] = []
    live_tracks: List[Dict[str, Any]] = []
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            for query in _MOOD_QUERIES[mood]:
                page = await _freesound_search(client, query, max_results)
                live_tracks.extend(page)
                if len(live_tracks) >= max_results:
                    break
    except Exception as exc:
        logger.info("ambient_live_failed", extra={"error": str(exc)})
        notes.append(f"live search error: {exc}")

    latency_ms = (time.perf_counter() - start) * 1000

    live_tracks = _filter_duration(live_tracks, min_duration, max_duration)
    # De-dupe by id
    seen: set = set()
    deduped_live: List[Dict[str, Any]] = []
    for t in live_tracks:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        deduped_live.append(dict(t, mood=mood))

    if deduped_live and len(deduped_live) >= max_results:
        result_tracks = deduped_live[:max_results]
        source = "live"
        provider = "freesound"
    elif deduped_live and include_fallback:
        curated = _curated_for_mood(mood, max_results - len(deduped_live))
        curated = _filter_duration(curated, min_duration, max_duration)
        result_tracks = (deduped_live + curated)[:max_results]
        source = "mixed"
        provider = "mixed"
        notes.append("live results topped up from curated library")
    else:
        curated = _curated_for_mood(mood, max_results)
        curated = _filter_duration(curated, min_duration, max_duration)
        result_tracks = curated
        source = "fallback"
        provider = "curated"
        if not deduped_live:
            notes.append(
                "Freesound unavailable or key missing — served curated library"
            )

    ttl = _CACHE_TTL_SECONDS if source != "fallback" else _NEGATIVE_CACHE_TTL
    try:
        await cache.set(
            key,
            {"tracks": result_tracks, "provider": provider, "notes": notes},
            ttl=ttl,
        )
    except Exception:  # pragma: no cover
        pass

    logger.info(
        "ambient_searched",
        extra={
            "mood": mood,
            "source": source,
            "provider": provider,
            "result_count": len(result_tracks),
            "latency_ms": round(latency_ms, 1),
        },
    )

    return {
        "mood": mood,
        "tracks": result_tracks,
        "source": source,
        "provider": provider,
        "cache_key": key,
        "notes": notes,
    }


# ─── Recommendation helper ─────────────────────────────────────────────────

def _mood_from_sentiment(sentiment: float, emotion: Optional[str]) -> str:
    """Map (sentiment_compound, dominant_emotion) → preferred ambient mood.

    Pure, deterministic rule table — keeps recommendations predictable.
    """
    emo = (emotion or "").lower()
    if any(k in emo for k in ("anx", "fear", "worry")):
        return "calm"
    if any(k in emo for k in ("sad", "grief")):
        return "ground"
    if any(k in emo for k in ("ang", "rage", "disgust")):
        return "ground"
    if any(k in emo for k in ("joy", "happ", "love")):
        return "uplift"
    if sentiment >= 0.4:
        return "uplift"
    if sentiment >= 0.1:
        return "focus"
    if sentiment <= -0.4:
        return "calm"
    if sentiment <= -0.1:
        return "ground"
    return "focus"


async def recommend_ambient(
    *, sentiment_score: float, dominant_emotion: Optional[str], max_results: int = 4,
) -> Dict[str, Any]:
    """Pick a mood from sentiment/emotion then surface tracks."""
    mood = _mood_from_sentiment(sentiment_score, dominant_emotion)
    result = await search_ambient(mood=mood, max_results=max_results)
    # The recommendation response reuses the same shape for consistency;
    # we append a note explaining *why* we picked this mood.
    result.setdefault("notes", []).insert(
        0,
        f"Recommended '{mood}' based on sentiment {sentiment_score:+.2f}"
        + (f" and dominant emotion '{dominant_emotion}'" if dominant_emotion else ""),
    )
    return result
