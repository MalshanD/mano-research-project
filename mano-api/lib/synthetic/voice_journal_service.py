"""
Voice Journal analytics pipeline.

Stages
------
1. **Transcription** — If the caller supplies ``audio_url`` we route to a
   pluggable transcription backend (HF Whisper inference API primary;
   graceful "degraded" response if no key is configured). Callers that
   already have transcripts in hand skip this stage entirely.
2. **Sentiment** — VADER compound score + categorical label. VADER is a
   deterministic, CPU-light lexicon model (no VRAM cost) and is already a
   requirements.txt dep for the chat upgrade.
3. **Emotion** — Optional HF zero-shot classifier. Uses the same free-tier
   API key as the narrative service; degrades to a VADER-derived pseudo-
   distribution if HF is unreachable so the dashboard never renders a
   blank panel.
4. **Themes** — Frequency / IDF-lite keyword extraction over the transcript
   with an English stop-word list. Deterministic, no network.
5. **Suggested action** — Deterministic rule table mapping
   (sentiment_label × dominant_emotion) → a short, gentle nudge. Never
   prescribes treatment; always defers to professional help on amber/red
   signals.

The entire pipeline returns a single ``VoiceJournalResponse`` with a
source-tag envelope — downstream UIs never need to inspect provider errors.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import HUGGINGFACE_BASE_URL, settings
from lib.infra.cache import get_cache
from lib.infra.security import sanitize_prompt, sanitize_text
from schemas.synthetic.voice_journal_schema import (
    EmotionScore,
    ThemeKeyword,
    VoiceJournalRequest,
    VoiceJournalResponse,
)

logger = logging.getLogger(__name__)


# ─── Tuning ────────────────────────────────────────────────────────────────

_WHISPER_MODEL = "openai/whisper-small"           # HF inference — small fits free-tier budget.
_EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"

_TRANSCRIBE_TIMEOUT = 25.0   # Audio can be several MB; leave headroom.
_EMOTION_TIMEOUT = 10.0

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB — HF inference hard cap.

_CACHE_TTL_TRANSCRIPT = 6 * 3600      # 6h — same audio URL re-analysed cheaply.
_CACHE_TTL_EMOTION = 2 * 3600         # 2h — same transcript re-classified cheaply.


# ─── Static resources ─────────────────────────────────────────────────────

# Minimal English stop-word set — intentionally small so we never drop clinical
# nouns like "anxious", "grief", etc. Extend via config if needed.
_STOPWORDS = frozenset("""
a about above after again against all am an and any are aren as at be because
been before being below between both but by can could did do does doing don
down during each few for from further had has have having he her here hers
herself him himself his how i if in into is isn it its itself just like me
might more most my myself no nor not now of off on once only or other our
ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under
until up very was we were what when where which while who whom why will with
would you your yours yourself yourselves
""".split())

# Conservative crisis-language heuristic. We deliberately keep this tight —
# the goal is to raise a UI safety banner, not to gate responses. False
# positives are acceptable; false negatives on obvious phrases are not.
_CRISIS_PATTERNS = [
    re.compile(r"\b(kill|hurt|harm)\s+(myself|me)\b", re.IGNORECASE),
    re.compile(r"\bsuicid(e|al)\b", re.IGNORECASE),
    re.compile(r"\b(end|take)\s+my\s+life\b", re.IGNORECASE),
    re.compile(r"\bi\s+(want|wish|plan)\s+to\s+die\b", re.IGNORECASE),
    re.compile(r"\bno\s+reason\s+to\s+live\b", re.IGNORECASE),
    re.compile(r"\bcan'?t\s+go\s+on\b", re.IGNORECASE),
]


# ─── VADER (lazy singleton) ───────────────────────────────────────────────

_vader_singleton: Any = None


def _get_vader() -> Any:
    """Lazy-load the VADER analyser. Kept out of module scope so imports are
    cheap and a missing dep doesn't prevent the rest of the app from booting."""
    global _vader_singleton
    if _vader_singleton is not None:
        return _vader_singleton
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader_singleton = SentimentIntensityAnalyzer()
    except Exception as exc:  # pragma: no cover — should never happen in prod
        logger.warning("vader_unavailable", extra={"error": str(exc)})
        _vader_singleton = None
    return _vader_singleton


def _sentiment_label(compound: float) -> str:
    # VADER convention, widened slightly so "neutral" isn't razor-thin.
    if compound >= 0.6:
        return "very_positive"
    if compound >= 0.15:
        return "positive"
    if compound <= -0.6:
        return "very_negative"
    if compound <= -0.15:
        return "negative"
    return "neutral"


# ─── Transcription ────────────────────────────────────────────────────────

async def _download_audio(url: str) -> Optional[bytes]:
    """Download audio with a size cap. Returns None on any failure."""
    try:
        async with httpx.AsyncClient(timeout=_TRANSCRIBE_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.info("audio_download_non_200", extra={"status": resp.status_code})
            return None
        data = resp.content
        if len(data) > _MAX_AUDIO_BYTES:
            logger.info("audio_too_large", extra={"bytes": len(data)})
            return None
        return data
    except Exception as exc:
        logger.info("audio_download_failed", extra={"error": str(exc)})
        return None


async def _hf_transcribe(audio_bytes: bytes, language_hint: Optional[str]) -> Optional[str]:
    """Send audio to the HF inference Whisper endpoint. Returns the transcript
    text, or None on failure. Never raises."""
    if not settings.huggingface_api_key:
        return None
    url = f"{HUGGINGFACE_BASE_URL}/{_WHISPER_MODEL}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_key}",
        "Content-Type": "application/octet-stream",
    }
    # The HF inference API accepts raw bytes for audio models.
    try:
        async with httpx.AsyncClient(timeout=_TRANSCRIBE_TIMEOUT) as client:
            resp = await client.post(url, content=audio_bytes, headers=headers)
    except Exception as exc:
        logger.info("hf_whisper_failed", extra={"error": str(exc)})
        return None

    if resp.status_code != 200:
        logger.info("hf_whisper_non_200", extra={"status": resp.status_code})
        return None

    try:
        data = resp.json()
    except Exception:
        return None
    # Response shape: {"text": "..."} for most audio models.
    if isinstance(data, dict):
        text = data.get("text") or ""
        return text.strip() or None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return (data[0].get("text") or "").strip() or None
    return None


async def _transcribe(request: VoiceJournalRequest) -> Tuple[str, str, List[str]]:
    """Resolve the transcript. Returns ``(transcript, source, notes)``."""
    notes: List[str] = []

    if request.transcript_text:
        cleaned = sanitize_text(request.transcript_text, max_length=8000)
        return cleaned, "provided", notes

    if not request.audio_url:
        # VoiceJournalRequest's model validator guarantees one of the two is set,
        # but we keep a defensive branch to avoid a TypeError under odd inputs.
        return "", "degraded", ["no input provided"]

    cache = get_cache()
    key = f"voice:transcript:{hashlib.sha256(request.audio_url.encode('utf-8')).hexdigest()[:24]}"
    try:
        cached = await cache.get(key)
    except Exception:  # pragma: no cover
        cached = None
    if cached and isinstance(cached, dict):
        return cached.get("transcript", ""), "live", ["transcript served from cache"]

    audio = await _download_audio(request.audio_url)
    if audio is None:
        notes.append("audio download failed or exceeded 25 MB cap")
        return "", "degraded", notes

    transcript = await _hf_transcribe(audio, request.language_hint)
    if not transcript:
        notes.append("HF Whisper inference unavailable — transcript missing")
        return "", "degraded", notes

    cleaned = sanitize_text(transcript, max_length=8000)
    try:
        await cache.set(key, {"transcript": cleaned}, ttl=_CACHE_TTL_TRANSCRIPT)
    except Exception:  # pragma: no cover
        pass
    return cleaned, "live", notes


# ─── Emotion classification ───────────────────────────────────────────────

def _fallback_emotion_distribution(sentiment_compound: float) -> List[EmotionScore]:
    """Derive a coarse 4-way emotion distribution from the VADER compound
    score. Intentionally simple — the UI renders this as "degraded" so nobody
    mistakes it for a real classifier output."""
    if sentiment_compound >= 0.4:
        return [
            EmotionScore(label="joy", score=0.55),
            EmotionScore(label="calm", score=0.25),
            EmotionScore(label="neutral", score=0.15),
            EmotionScore(label="sadness", score=0.05),
        ]
    if sentiment_compound <= -0.4:
        return [
            EmotionScore(label="sadness", score=0.45),
            EmotionScore(label="anxiety", score=0.30),
            EmotionScore(label="anger", score=0.15),
            EmotionScore(label="neutral", score=0.10),
        ]
    return [
        EmotionScore(label="neutral", score=0.60),
        EmotionScore(label="calm", score=0.20),
        EmotionScore(label="sadness", score=0.10),
        EmotionScore(label="joy", score=0.10),
    ]


async def _hf_emotion(transcript: str) -> Optional[List[EmotionScore]]:
    """Query the HF emotion classifier. Returns normalised scores or None."""
    if not settings.huggingface_api_key:
        return None
    url = f"{HUGGINGFACE_BASE_URL}/{_EMOTION_MODEL}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": sanitize_prompt(transcript, max_length=2000)}
    try:
        async with httpx.AsyncClient(timeout=_EMOTION_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except Exception as exc:
        logger.info("hf_emotion_failed", extra={"error": str(exc)})
        return None
    if resp.status_code != 200:
        logger.info("hf_emotion_non_200", extra={"status": resp.status_code})
        return None
    try:
        data = resp.json()
    except Exception:
        return None

    # Response may be [[{label,score}, ...]] or [{label,score}, ...].
    if isinstance(data, list) and data and isinstance(data[0], list):
        inner = data[0]
    elif isinstance(data, list):
        inner = data
    else:
        return None

    out: List[EmotionScore] = []
    for item in inner:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip().lower()
        try:
            score = float(item.get("score") or 0.0)
        except (TypeError, ValueError):
            continue
        if not label:
            continue
        out.append(EmotionScore(label=label, score=max(0.0, min(1.0, score))))
    out.sort(key=lambda e: e.score, reverse=True)
    return out or None


async def _classify_emotion(
    transcript: str, *, enabled: bool, sentiment_compound: float,
) -> Tuple[List[EmotionScore], str]:
    if not enabled:
        return [], "disabled"
    if not transcript:
        return [], "disabled"

    cache = get_cache()
    key = f"voice:emotion:{hashlib.sha256(transcript.encode('utf-8')).hexdigest()[:24]}"
    try:
        cached = await cache.get(key)
    except Exception:  # pragma: no cover
        cached = None
    if cached and isinstance(cached, list):
        return [EmotionScore(**e) for e in cached], "cached"

    live = await _hf_emotion(transcript)
    if live:
        try:
            await cache.set(key, [e.model_dump() for e in live], ttl=_CACHE_TTL_EMOTION)
        except Exception:  # pragma: no cover
            pass
        return live, "live"

    return _fallback_emotion_distribution(sentiment_compound), "fallback"


# ─── Theme extraction ─────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")


def _extract_themes(transcript: str, max_themes: int) -> List[ThemeKeyword]:
    """Return up to ``max_themes`` keyword-weight pairs.

    Algorithm: lower-case tokenise, drop stopwords, count, divide each count by
    the maximum count to produce a [0, 1] weight. Not state-of-the-art but
    deterministic, dependency-free and fast enough for hot paths.
    """
    if not transcript:
        return []
    tokens = [t.lower() for t in _WORD_RE.findall(transcript)]
    tokens = [t for t in tokens if t not in _STOPWORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    top = counts.most_common(max_themes)
    if not top:
        return []
    peak = top[0][1] or 1
    return [ThemeKeyword(term=term, weight=round(count / peak, 3)) for term, count in top]


# ─── Suggested-action rule table ──────────────────────────────────────────

_ACTION_TABLE: Dict[str, str] = {
    # sentiment_label × bucketed dominant emotion → nudge
    "very_negative|sadness": (
        "Be gentle with yourself today. A short walk or a message to someone you "
        "trust can help the weight feel more portable."
    ),
    "very_negative|anxiety": (
        "Your nervous system is working hard. Try three slow breaths out to four "
        "counts — longer exhales tell the body it's safe to rest."
    ),
    "very_negative|anger": (
        "Anger often carries important information. Name what the unmet need "
        "behind it is before deciding what to do."
    ),
    "negative|sadness": (
        "A small ritual — tea, sunlight, a familiar song — can shift the "
        "background of a hard day without demanding too much."
    ),
    "negative|anxiety": (
        "Write down the worry in one sentence, then the smallest action you could "
        "take today. Shrinking the loop usually shrinks the feeling."
    ),
    "neutral|neutral": (
        "A steady day is a good baseline. Consider one small act of care — "
        "stretching, water, stepping outside — to anchor it."
    ),
    "positive|joy": (
        "Notice what contributed to this. Naming the ingredients makes them "
        "easier to recreate on a harder day."
    ),
    "very_positive|joy": (
        "Savour this, but don't rush to package it. Let the good day just be a "
        "good day."
    ),
}

_DEFAULT_ACTION = (
    "Thanks for checking in. Staying in regular contact with how you feel is one "
    "of the most reliable ways to catch shifts early."
)

_CRISIS_ACTION = (
    "Some of what you wrote suggests you're in a lot of pain right now. You don't "
    "have to face this alone — please consider reaching out to a trusted person "
    "or a local crisis line. If you're in immediate danger, contact emergency "
    "services."
)


def _bucket_emotion(label: Optional[str]) -> str:
    if not label:
        return "neutral"
    label = label.lower()
    if "joy" in label or "happ" in label or "love" in label:
        return "joy"
    if "sad" in label or "grief" in label:
        return "sadness"
    if "fear" in label or "anx" in label or "worry" in label:
        return "anxiety"
    if "ang" in label or "rage" in label or "disgust" in label:
        return "anger"
    if "calm" in label or "neutral" in label:
        return "neutral"
    return "neutral"


def _suggest_action(
    sentiment_label: str, dominant_emotion: Optional[str], crisis: bool,
) -> str:
    if crisis:
        return _CRISIS_ACTION
    bucket = _bucket_emotion(dominant_emotion)
    return _ACTION_TABLE.get(f"{sentiment_label}|{bucket}", _DEFAULT_ACTION)


# ─── Crisis detection ─────────────────────────────────────────────────────

def _has_crisis_language(text: str) -> bool:
    if not text:
        return False
    return any(pat.search(text) for pat in _CRISIS_PATTERNS)


# ─── Orchestrator ─────────────────────────────────────────────────────────

async def analyse_voice_journal(request: VoiceJournalRequest) -> VoiceJournalResponse:
    """Full pipeline — transcription + sentiment + emotion + themes + nudge.

    Never raises. Any stage may degrade independently; the response's
    source tags + notes list make the degradation legible to the frontend.
    """
    start = time.perf_counter()

    # 1. Transcript
    transcript, transcription_source, notes = await _transcribe(request)

    # 2. Sentiment (VADER)
    analyser = _get_vader()
    if analyser is not None and transcript:
        scores = analyser.polarity_scores(transcript)
        compound = float(scores.get("compound", 0.0))
    else:
        compound = 0.0
        if transcript:
            notes.append("VADER analyser unavailable — sentiment defaulted to neutral")

    sentiment_label = _sentiment_label(compound)

    # 3. Emotion (HF, optional)
    emotion, emotion_source = await _classify_emotion(
        transcript,
        enabled=bool(request.include_emotion and transcript),
        sentiment_compound=compound,
    )
    dominant = emotion[0].label if emotion else None

    # 4. Themes
    themes = _extract_themes(transcript, request.max_themes) if request.include_themes else []

    # 5. Crisis heuristic + action
    crisis = _has_crisis_language(transcript)
    if crisis:
        notes.append("Crisis-language heuristic matched — UI should surface safety resources.")

    action = _suggest_action(sentiment_label, dominant, crisis)

    word_count = len(re.findall(r"\S+", transcript)) if transcript else 0

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "voice_journal_analysed",
        extra={
            "transcription_source": transcription_source,
            "emotion_source": emotion_source,
            "word_count": word_count,
            "sentiment_label": sentiment_label,
            "dominant_emotion": dominant,
            "crisis_flag": crisis,
            "latency_ms": round(latency_ms, 1),
        },
    )

    return VoiceJournalResponse(
        transcript=transcript,
        word_count=word_count,
        sentiment_score=round(compound, 4),
        sentiment_label=sentiment_label,
        emotion_distribution=emotion,
        dominant_emotion=dominant,
        themes=themes,
        suggested_action=action,
        transcription_source=transcription_source,
        emotion_source=emotion_source,
        analysed_at=datetime.utcnow(),
        notes=notes,
        crisis_language_detected=crisis,
    )


# ─── Trend aggregation (pure function over historical responses) ──────────

def summarise_trend(
    recent: List[Dict[str, Any]], *, window_days: int = 14, top_k: int = 5,
) -> Dict[str, Any]:
    """Given a list of stored VoiceJournalResponse-shaped dicts (most recent
    last), return aggregate stats suitable for a dashboard trend card.

    Pure — no I/O, no DB coupling. Callers provide the raw rows.
    """
    notes: List[str] = []
    if not recent:
        return {
            "samples": 0,
            "mean_sentiment": None,
            "sentiment_trend": "insufficient_data",
            "top_emotions": [],
            "top_themes": [],
            "window_start": None,
            "window_end": None,
            "notes": ["No journal entries in window"],
        }

    samples = len(recent)
    sentiments = [float(r.get("sentiment_score") or 0.0) for r in recent]
    mean_sent = sum(sentiments) / samples

    # Trend — slope of last vs first third.
    if samples < 4:
        trend = "insufficient_data"
        notes.append("Need at least 4 entries for a trend read")
    else:
        split = max(1, samples // 3)
        first = sum(sentiments[:split]) / split
        last = sum(sentiments[-split:]) / split
        delta = last - first
        if delta > 0.15:
            trend = "improving"
        elif delta < -0.15:
            trend = "worsening"
        else:
            trend = "stable"

    # Aggregate emotions.
    emo_totals: Dict[str, List[float]] = {}
    for row in recent:
        for emo in row.get("emotion_distribution") or []:
            label = emo.get("label")
            try:
                score = float(emo.get("score") or 0.0)
            except (TypeError, ValueError):
                continue
            if not label:
                continue
            emo_totals.setdefault(label, []).append(score)
    emo_summary = sorted(
        (
            {
                "label": label,
                "mean_score": round(sum(v) / len(v), 4),
                "peak_score": round(max(v), 4),
                "sample_count": len(v),
            }
            for label, v in emo_totals.items()
        ),
        key=lambda e: e["mean_score"], reverse=True,
    )[:top_k]

    # Aggregate themes.
    theme_counts: Counter = Counter()
    for row in recent:
        for theme in row.get("themes") or []:
            term = theme.get("term")
            try:
                weight = float(theme.get("weight") or 0.0)
            except (TypeError, ValueError):
                continue
            if term:
                theme_counts[term] += weight
    total_weight = sum(theme_counts.values()) or 1.0
    theme_summary = [
        {"term": term, "weight": round(weight / total_weight, 4)}
        for term, weight in theme_counts.most_common(top_k)
    ]

    window_start = recent[0].get("analysed_at")
    window_end = recent[-1].get("analysed_at")

    return {
        "samples": samples,
        "mean_sentiment": round(mean_sent, 4),
        "sentiment_trend": trend,
        "top_emotions": emo_summary,
        "top_themes": theme_summary,
        "window_start": window_start,
        "window_end": window_end,
        "notes": notes,
    }
