"""
Dashboard Intelligence aggregator.

Fires every third-party panel in parallel via ``asyncio.gather`` with
``return_exceptions=True`` so one slow / failed provider cannot starve the
others. Results are assembled into a single ``DashboardResponse`` with a
per-panel ``PanelStatus`` envelope.

Key design choices
------------------
* **Partial failure is expected.** A dashboard that is 80 % populated is
  vastly better than a dashboard that 500s because one upstream tripped.
* **Short cache TTL.** Dashboards are refreshed on load, so we cache for
  30 s — enough to debounce double-clicks and mount/unmount storms, short
  enough that fresh data is visible within a minute.
* **No trajectory forecasting here.** The trajectory service requires the
  risk + intervention ML services (heavy, GPU-bound). The caller forwards
  a pre-computed ``TrajectorySummary`` if they have one. This keeps the
  aggregator latency bounded by *network* calls, not model inference.
* **Explicit opt-in per panel.** Absent input → panel simply omitted from
  response. Nothing fabricated.

The event bus publishes a single "dashboard_generated" event with the
per-panel statuses so the telemetry sink (Component 2) can observe upstream
health without scraping every service.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lib.infra.cache import get_cache
from lib.synthetic.affirmation_service import get_daily_affirmation
from lib.synthetic.ambient_sound_service import recommend_ambient
from lib.synthetic.evidence_service import fetch_evidence
from lib.synthetic.narrative_v2_service import generate_narrative
from lib.synthetic.weather_mood_service import current_forecast
from schemas.synthetic.affirmation_schema import AffirmationResponse, AffirmationTone
from schemas.synthetic.ambient_sound_schema import (
    AmbientSearchResponse,
    SoundMood,
    SoundTrack,
)
from schemas.synthetic.dashboard_schema import (
    DashboardRequest,
    DashboardResponse,
    PanelStatus,
)
from schemas.synthetic.evidence_schema import EvidenceCard, EvidenceResponse
from schemas.synthetic.narrative_schema import (
    NarrativeLength,
    NarrativeResponse,
    NarrativeTone,
)
from schemas.synthetic.weather_mood_schema import ForecastResponse

logger = logging.getLogger(__name__)


_CACHE_TTL_SECONDS = 30  # very short — dashboards re-mount aggressively
_PANEL_HARD_TIMEOUT = 18.0  # ceiling per panel; narrative can legally take ~10s


# ─── Cache key ────────────────────────────────────────────────────────────

def _cache_key(req: DashboardRequest) -> str:
    payload = req.model_dump()
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return f"dashboard:v2:{hashlib.sha256(blob).hexdigest()[:24]}"


# ─── Panel wrappers ───────────────────────────────────────────────────────
#
# Each wrapper returns ``(PanelStatus, result_dict_or_None)``. A status
# value of ``error`` means the panel never loaded; the frontend can
# render an empty state with the error string.

async def _panel_narrative(req: DashboardRequest) -> Tuple[PanelStatus, Optional[NarrativeResponse]]:
    if not req.trajectory:
        return (
            PanelStatus(name="narrative", status="ok", source="skipped"),
            None,
        )
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            generate_narrative(
                trajectory=req.trajectory,
                tone=req.narrative_tone,
                length=req.narrative_length,
                patient_voice=req.patient_voice,
            ),
            timeout=_PANEL_HARD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        latency = (time.perf_counter() - start) * 1000
        return (
            PanelStatus(
                name="narrative", status="error",
                error=f"timeout after {_PANEL_HARD_TIMEOUT}s",
                latency_ms=round(latency, 1),
            ),
            None,
        )
    except Exception as exc:
        return (
            PanelStatus(name="narrative", status="error", error=str(exc)),
            None,
        )
    latency = (time.perf_counter() - start) * 1000
    payload = NarrativeResponse(
        narrative=result.narrative,
        intervention=req.trajectory.intervention,
        tone=req.narrative_tone,
        length=req.narrative_length,
        source=result.source,
        provider=result.provider,
        notes=result.notes,
    )
    status = "ok" if result.source != "fallback" else "degraded"
    return (
        PanelStatus(
            name="narrative", status=status, source=result.source,
            provider=result.provider, latency_ms=round(latency, 1),
        ),
        payload,
    )


async def _panel_evidence(req: DashboardRequest) -> Tuple[PanelStatus, Optional[EvidenceResponse]]:
    intervention = req.evidence_intervention or (
        req.trajectory.intervention.lower().replace(" ", "_") if req.trajectory else None
    )
    if not intervention:
        return (
            PanelStatus(name="evidence", status="ok", source="skipped"),
            None,
        )
    start = time.perf_counter()
    try:
        raw = await asyncio.wait_for(
            fetch_evidence(
                intervention, max_results=req.evidence_max_cards, include_abstract=True,
            ),
            timeout=_PANEL_HARD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return (
            PanelStatus(name="evidence", status="error", error="timeout"),
            None,
        )
    except Exception as exc:
        return (
            PanelStatus(name="evidence", status="error", error=str(exc)),
            None,
        )
    latency = (time.perf_counter() - start) * 1000
    cards = [EvidenceCard(**c) for c in raw.get("cards", [])]
    payload = EvidenceResponse(
        intervention=raw.get("intervention", intervention),
        cards=cards,
        source=raw.get("source", "fallback"),
        provider=raw.get("provider", "pubmed"),
        cache_key=raw.get("cache_key"),
        notes=raw.get("notes", []),
    )
    status = "ok" if (payload.source != "fallback" or payload.cards) else "degraded"
    return (
        PanelStatus(
            name="evidence", status=status, source=payload.source,
            provider=payload.provider, latency_ms=round(latency, 1),
        ),
        payload,
    )


async def _panel_weather(req: DashboardRequest) -> Tuple[PanelStatus, Optional[ForecastResponse]]:
    if not req.city:
        return (
            PanelStatus(name="weather", status="ok", source="skipped"),
            None,
        )
    start = time.perf_counter()
    loop = asyncio.get_running_loop()
    try:
        # current_forecast is a sync function — offload to the default executor
        # so it doesn't block the aggregator loop.
        raw = await asyncio.wait_for(
            loop.run_in_executor(None, current_forecast, req.city),
            timeout=_PANEL_HARD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return (
            PanelStatus(name="weather", status="error", error="timeout"),
            None,
        )
    except Exception as exc:
        return (
            PanelStatus(name="weather", status="error", error=str(exc)),
            None,
        )
    latency = (time.perf_counter() - start) * 1000
    payload = ForecastResponse(**raw)
    status = "ok" if payload.source != "fallback" else "degraded"
    return (
        PanelStatus(
            name="weather", status=status, source=payload.source,
            provider=payload.provider, latency_ms=round(latency, 1),
        ),
        payload,
    )


async def _panel_affirmation(req: DashboardRequest) -> Tuple[PanelStatus, Optional[AffirmationResponse]]:
    start = time.perf_counter()
    trajectory_shape = req.trajectory.trajectory_shape if req.trajectory else None
    try:
        raw = await asyncio.wait_for(
            get_daily_affirmation(
                tone=None,
                sentiment_score=req.sentiment_score,
                trajectory_shape=trajectory_shape,
            ),
            timeout=_PANEL_HARD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return (
            PanelStatus(name="affirmation", status="error", error="timeout"),
            None,
        )
    except Exception as exc:
        return (
            PanelStatus(name="affirmation", status="error", error=str(exc)),
            None,
        )
    latency = (time.perf_counter() - start) * 1000
    payload = AffirmationResponse(
        text=raw["text"],
        tone=AffirmationTone(raw["tone"]),
        author=raw.get("author"),
        source=raw["source"],
        provider=raw["provider"],
        notes=raw.get("notes", []),
    )
    status = "ok" if payload.source != "fallback" else "degraded"
    return (
        PanelStatus(
            name="affirmation", status=status, source=payload.source,
            provider=payload.provider, latency_ms=round(latency, 1),
        ),
        payload,
    )


async def _panel_ambient(req: DashboardRequest) -> Tuple[PanelStatus, Optional[AmbientSearchResponse]]:
    if not req.include_ambient:
        return (
            PanelStatus(name="ambient", status="ok", source="skipped"),
            None,
        )
    # Only build a recommendation if we at least have a sentiment hint.
    if req.sentiment_score is None and not req.dominant_emotion:
        return (
            PanelStatus(name="ambient", status="ok", source="skipped"),
            None,
        )
    start = time.perf_counter()
    try:
        raw = await asyncio.wait_for(
            recommend_ambient(
                sentiment_score=req.sentiment_score or 0.0,
                dominant_emotion=req.dominant_emotion,
                max_results=req.ambient_max_results,
            ),
            timeout=_PANEL_HARD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return (
            PanelStatus(name="ambient", status="error", error="timeout"),
            None,
        )
    except Exception as exc:
        return (
            PanelStatus(name="ambient", status="error", error=str(exc)),
            None,
        )
    latency = (time.perf_counter() - start) * 1000
    payload = AmbientSearchResponse(
        mood=SoundMood(raw["mood"]),
        tracks=[SoundTrack(**t) for t in raw.get("tracks", [])],
        source=raw["source"],
        provider=raw["provider"],
        cache_key=raw.get("cache_key"),
        notes=raw.get("notes", []),
    )
    status = "ok" if payload.source != "fallback" else "degraded"
    return (
        PanelStatus(
            name="ambient", status=status, source=payload.source,
            provider=payload.provider, latency_ms=round(latency, 1),
        ),
        payload,
    )


# ─── Orchestrator ─────────────────────────────────────────────────────────

async def build_dashboard(request: DashboardRequest) -> DashboardResponse:
    """Run every panel concurrently and assemble a single response.

    Never raises. Each panel's failure is captured in the response envelope
    so the frontend can render a per-panel fallback.
    """

    cache = get_cache()
    key = _cache_key(request)
    try:
        hit = await cache.get(key)
    except Exception:  # pragma: no cover
        hit = None
    if hit:
        try:
            response = DashboardResponse(**hit)
            response.cache_hit = True
            return response
        except Exception as exc:
            logger.info("dashboard_cache_decode_failed", extra={"error": str(exc)})

    start = time.perf_counter()
    results = await asyncio.gather(
        _panel_narrative(request),
        _panel_evidence(request),
        _panel_weather(request),
        _panel_affirmation(request),
        _panel_ambient(request),
        return_exceptions=True,
    )

    panels: List[PanelStatus] = []
    panel_data: Dict[str, Any] = {
        "narrative": None,
        "evidence": None,
        "weather": None,
        "affirmation": None,
        "ambient": None,
    }
    order = ("narrative", "evidence", "weather", "affirmation", "ambient")

    for name, outcome in zip(order, results):
        if isinstance(outcome, BaseException):
            panels.append(PanelStatus(name=name, status="error", error=str(outcome)))
            continue
        status, payload = outcome
        panels.append(status)
        panel_data[name] = payload

    # Top-level notes — only include panels that fell back, so the UI can
    # render a single "some data is degraded" banner at the top if needed.
    notes: List[str] = []
    for p in panels:
        if p.status == "degraded":
            notes.append(f"{p.name} panel served degraded data ({p.source})")
        elif p.status == "error":
            notes.append(f"{p.name} panel failed: {p.error}")

    response = DashboardResponse(
        generated_at=datetime.utcnow(),
        cache_hit=False,
        narrative=panel_data["narrative"],
        evidence=panel_data["evidence"],
        weather_forecast=panel_data["weather"],
        affirmation=panel_data["affirmation"],
        ambient=panel_data["ambient"],
        panels=panels,
        notes=notes,
    )

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "dashboard_generated",
        extra={
            "latency_ms": round(latency_ms, 1),
            "panel_statuses": [p.status for p in panels],
            "notes": notes,
        },
    )

    try:
        await cache.set(
            key, response.model_dump(mode="json"), ttl=_CACHE_TTL_SECONDS,
        )
    except Exception:  # pragma: no cover
        pass

    return response
