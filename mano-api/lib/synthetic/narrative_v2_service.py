"""
Future-Self Narrative Engine (v2).

v2 differences from the legacy ``FutureSelfNarrativeEngine``
-----------------------------------------------------------
* Reads credentials + URLs from ``core.config.settings`` (not ``os.getenv``),
  so swapping environments is a single-file change.
* Fallback chain: Groq → Gemini → HuggingFace → deterministic template.
* Cache: Redis-backed via ``lib.infra.cache`` with in-memory fallback; keyed on
  a stable hash of the (trajectory, tone, length, sanitised patient_voice)
  tuple. A 1-hour TTL means repeat views don't re-spend the free-tier quota.
* Output carries a source-tag envelope (live/cached/fallback) + provider name
  so the frontend can render trust badges.
* All free-text fields pass through ``lib.infra.security.sanitize_prompt``
  before interpolation — no jailbreak-friendly characters make it into the
  system prompt.
* Non-blocking: each provider has a strict timeout so one slow backend can't
  delay the whole fallback chain.

This service is a drop-in replacement; the legacy endpoint in
``enhanced_c1_route.py`` continues to work against the old service until the
frontend migrates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import (
    GEMINI_BASE_URL,
    GROQ_BASE_URL,
    HUGGINGFACE_BASE_URL,
    settings,
)
from lib.infra.cache import get_cache
from lib.infra.security import sanitize_prompt, sanitize_text
from schemas.synthetic.narrative_schema import (
    NarrativeLength,
    NarrativeTone,
    TrajectorySummary,
)

logger = logging.getLogger(__name__)


# Per-provider hard timeouts (seconds). Groq typically responds in <500ms;
# we keep the ceiling low so a hang doesn't starve the fallback chain.
_GROQ_TIMEOUT = 8.0
_GEMINI_TIMEOUT = 10.0
_HF_TIMEOUT = 12.0

# Narrative length → target max_tokens mapping. We intentionally undershoot so
# the free-tier quotas stretch further.
_LENGTH_TOKENS = {
    NarrativeLength.SHORT: 120,
    NarrativeLength.MEDIUM: 220,
    NarrativeLength.LONG: 360,
}

_CACHE_TTL_SECONDS = 3600  # 1 hour — same patient + same trajectory, same story.

# Model IDs per provider — kept small / fast so we stay under free-tier rate caps.
_GROQ_MODEL = "llama-3.1-8b-instant"
_GEMINI_MODEL = "gemini-1.5-flash"
_HF_MODEL = "HuggingFaceH4/zephyr-7b-beta"


# ─── Result envelope ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class NarrativeResult:
    narrative: str
    source: str           # live | cached | fallback
    provider: str         # groq | gemini | hf | template
    notes: List[str]


# ─── Prompt construction ──────────────────────────────────────────────────────

_TONE_INSTRUCTIONS = {
    NarrativeTone.HOPEFUL: "Tone: warm, optimistic, and encouraging — without being saccharine.",
    NarrativeTone.CLINICAL: "Tone: measured, clinical-but-human, grounded in observable changes.",
    NarrativeTone.NEUTRAL: "Tone: calm, matter-of-fact, neither optimistic nor pessimistic.",
}

_LENGTH_INSTRUCTIONS = {
    NarrativeLength.SHORT: "Length: 2–3 sentences.",
    NarrativeLength.MEDIUM: "Length: 4–6 sentences.",
    NarrativeLength.LONG: "Length: 7–10 sentences — a full micro-journal entry.",
}

_SYSTEM_PROMPT = (
    "You are the patient's 'future self' — the same person, writing back from "
    "the end of a short simulated trajectory. Use first person present tense. "
    "Focus on how things FEEL (sensory, emotional, day-to-day), not on clinical "
    "numbers. Never invent medical outcomes the data does not support. Never "
    "fabricate events, names, or diagnoses. Do not give medical advice."
)


def _build_user_prompt(
    trajectory: TrajectorySummary, tone: NarrativeTone,
    length: NarrativeLength, patient_voice: Optional[str],
) -> str:
    shape_phrase = {
        "improving": "the trend is improving",
        "worsening": "the trend is drifting worse",
        "stable": "things are holding steady",
        "oscillating": "things are fluctuating day-to-day",
    }.get(trajectory.trajectory_shape, "the trend is mixed")

    peak_phrase = ""
    if trajectory.peak_risk_day and trajectory.peak_risk_class:
        peak_phrase = (
            f" The hardest day in the window is day {trajectory.peak_risk_day} "
            f"({trajectory.peak_risk_class.value.lower()} risk)."
        )

    mean_phrase = ""
    if trajectory.mean_high_risk_probability is not None:
        mean_phrase = (
            f" Average high-risk probability across the horizon is "
            f"{trajectory.mean_high_risk_probability * 100:.0f}%."
        )

    voice_phrase = ""
    if patient_voice:
        voice_phrase = f'\nPatient preference note (sanitised): "{patient_voice}"\n'

    return (
        f"I just completed {trajectory.horizon_days} simulated days on "
        f"{trajectory.intervention} at intensity {trajectory.intensity:.2f}. "
        f"According to the simulation, {shape_phrase}.{peak_phrase}{mean_phrase}\n"
        f"{voice_phrase}\n"
        f"{_TONE_INSTRUCTIONS[tone]}\n"
        f"{_LENGTH_INSTRUCTIONS[length]}\n"
        "Write the journal entry now."
    )


# ─── Cache key ────────────────────────────────────────────────────────────────

def _cache_key(
    trajectory: TrajectorySummary, tone: NarrativeTone,
    length: NarrativeLength, patient_voice: Optional[str],
) -> str:
    """Stable hash of the inputs. Patient voice is sanitised first so minor
    whitespace differences don't bust the cache."""
    payload = {
        "intervention": trajectory.intervention,
        "intensity": round(trajectory.intensity, 2),
        "horizon_days": trajectory.horizon_days,
        "trajectory_shape": trajectory.trajectory_shape,
        "peak_risk_day": trajectory.peak_risk_day,
        "peak_risk_class": (
            trajectory.peak_risk_class.value if trajectory.peak_risk_class else None
        ),
        "mean_high_risk": (
            round(trajectory.mean_high_risk_probability, 2)
            if trajectory.mean_high_risk_probability is not None else None
        ),
        "tone": tone.value,
        "length": length.value,
        "patient_voice": sanitize_text(patient_voice or "", max_length=200),
    }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"narrative:v2:{hashlib.sha256(blob).hexdigest()[:24]}"


# ─── Provider calls ───────────────────────────────────────────────────────────

async def _call_groq(prompt: str, length: NarrativeLength) -> Optional[str]:
    if not settings.groq_api_key:
        return None
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.75,
        "max_tokens": _LENGTH_TOKENS[length],
    }
    async with httpx.AsyncClient(timeout=_GROQ_TIMEOUT) as client:
        resp = await client.post(GROQ_BASE_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.info("groq_non_200", extra={"status": resp.status_code})
        return None
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        return None
    return (choices[0].get("message", {}) or {}).get("content", "").strip() or None


async def _call_gemini(prompt: str, length: NarrativeLength) -> Optional[str]:
    if not settings.gemini_api_key:
        return None
    url = (
        f"{GEMINI_BASE_URL}/models/{_GEMINI_MODEL}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": _SYSTEM_PROMPT + "\n\n" + prompt}],
        }],
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": _LENGTH_TOKENS[length],
        },
    }
    async with httpx.AsyncClient(timeout=_GEMINI_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
    if resp.status_code != 200:
        logger.info("gemini_non_200", extra={"status": resp.status_code})
        return None
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    if not parts:
        return None
    return (parts[0].get("text") or "").strip() or None


async def _call_huggingface(prompt: str, length: NarrativeLength) -> Optional[str]:
    if not settings.huggingface_api_key:
        return None
    url = f"{HUGGINGFACE_BASE_URL}/{_HF_MODEL}"
    headers = {"Authorization": f"Bearer {settings.huggingface_api_key}"}
    payload = {
        "inputs": _SYSTEM_PROMPT + "\n\n" + prompt,
        "parameters": {
            "temperature": 0.75,
            "max_new_tokens": _LENGTH_TOKENS[length],
            "return_full_text": False,
        },
    }
    async with httpx.AsyncClient(timeout=_HF_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.info("hf_non_200", extra={"status": resp.status_code})
        return None
    data = resp.json()
    # HF sometimes returns a list, sometimes a dict with "generated_text".
    if isinstance(data, list) and data:
        return (data[0].get("generated_text") or "").strip() or None
    if isinstance(data, dict):
        return (data.get("generated_text") or "").strip() or None
    return None


# ─── Template fallback ────────────────────────────────────────────────────────

def _template_narrative(trajectory: TrajectorySummary, tone: NarrativeTone) -> str:
    """Deterministic narrative used when every provider fails or is unconfigured.

    Deliberately conservative phrasing — we never claim an outcome the
    trajectory doesn't support.
    """
    shape = trajectory.trajectory_shape
    if shape == "improving":
        body = (
            f"After {trajectory.horizon_days} days of {trajectory.intervention}, "
            "I can feel a small shift. It isn't dramatic, but the edges are softer. "
            "Showing up every day, even imperfectly, seems to matter."
        )
    elif shape == "worsening":
        body = (
            f"The last {trajectory.horizon_days} days on {trajectory.intervention} "
            "have been harder than I expected. I'm noticing where I struggle — "
            "and that noticing is itself a start. I'll talk this through with "
            "someone I trust."
        )
    elif shape == "oscillating":
        body = (
            f"This week on {trajectory.intervention} felt uneven — some days "
            "lighter, some days heavier. I'm learning to trust the average, not "
            "any one day."
        )
    else:
        body = (
            f"A quiet week on {trajectory.intervention}. Nothing dramatic — which "
            "is, in its own way, a kind of progress."
        )

    if tone == NarrativeTone.CLINICAL:
        # Same content, cooler register.
        body = body.replace("feel", "observe").replace("I can", "I")
    return body


# ─── Public entry point ───────────────────────────────────────────────────────

async def generate_narrative(
    *,
    trajectory: TrajectorySummary,
    tone: NarrativeTone = NarrativeTone.HOPEFUL,
    length: NarrativeLength = NarrativeLength.MEDIUM,
    patient_voice: Optional[str] = None,
) -> NarrativeResult:
    """Generate a Future-Self journal entry.

    The function never raises on provider failure — it returns a template
    narrative tagged as ``fallback`` instead. Raising would force every
    dashboard widget to handle errors, which is worse UX than a graceful
    degradation.
    """
    # 1. Sanitise the user free-text BEFORE anything else.
    safe_voice = sanitize_prompt(patient_voice) if patient_voice else None

    # 2. Cache lookup.
    cache = get_cache()
    key = _cache_key(trajectory, tone, length, safe_voice)
    try:
        hit = await cache.get(key)
    except Exception:  # pragma: no cover — cache is never hard-required
        hit = None
    if hit:
        return NarrativeResult(
            narrative=hit.get("narrative", ""),
            source="cached",
            provider=hit.get("provider", "unknown"),
            notes=hit.get("notes", []),
        )

    # 3. Build the prompt once; fallback chain reuses it.
    prompt = _build_user_prompt(trajectory, tone, length, safe_voice)
    notes: List[str] = []

    # 4. Walk the provider chain. Any exception inside a provider is caught
    #    and logged; we never leak a partial response to the caller.
    providers: Tuple[Tuple[str, Any], ...] = (
        ("groq", _call_groq),
        ("gemini", _call_gemini),
        ("hf", _call_huggingface),
    )

    for name, call in providers:
        start = time.perf_counter()
        try:
            text = await call(prompt, length)
        except Exception as exc:  # pragma: no cover — depends on network
            logger.info("narrative_provider_failed", extra={"provider": name, "error": str(exc)})
            notes.append(f"{name} unavailable")
            continue
        latency_ms = (time.perf_counter() - start) * 1000

        if text:
            logger.info(
                "narrative_generated",
                extra={"provider": name, "latency_ms": round(latency_ms, 1)},
            )
            # Cache on success only. TTL is short enough that a provider swap
            # during a deploy doesn't serve stale outputs for long.
            try:
                await cache.set(
                    key,
                    {"narrative": text, "provider": name, "notes": notes},
                    ttl=_CACHE_TTL_SECONDS,
                )
            except Exception:  # pragma: no cover
                pass
            return NarrativeResult(narrative=text, source="live", provider=name, notes=notes)

        notes.append(f"{name} empty response")

    # 5. Deterministic fallback.
    template = _template_narrative(trajectory, tone)
    notes.append("all providers unavailable — served template")
    return NarrativeResult(narrative=template, source="fallback", provider="template", notes=notes)
