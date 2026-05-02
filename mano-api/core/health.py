"""
MANO Health Check Endpoint.

Two-tier probing:

* ``GET /``        — liveness (handled in main.py). Confirms the process is up.
* ``GET /health``  — readiness (this module). Confirms every dependency the
                     AI engine needs is reachable.

Probe matrix
------------
models      — all five C1 frozen models loaded (lstm, simulator, agent,
              timegan, ctgan). Required for readiness.
database    — can issue a trivial ``SELECT 1``. Required for readiness.
cache       — Redis ping when Redis is the active backend; in-memory is
              always "reachable". NOT required for readiness — the app
              degrades to the in-memory fallback automatically.
event_bus   — in-process is always healthy; Kafka ping when configured.
              Not required for readiness for the same reason as cache.
scheduler   — APScheduler is running. Not required for readiness.

We return HTTP 503 only when a *hard* dependency fails (models, DB). Soft
dependencies surface in the JSON body so dashboards can flag degraded state
without triggering load-balancer removal.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from lib.infra.cache import get_cache
from lib.infra.event_bus import get_event_bus
from lib.infra.scheduler import get_scheduler

router = APIRouter(tags=["System"])


async def _probe_db() -> Dict[str, Any]:
    """Best-effort DB connectivity check. Works with both async + sync engines."""
    try:
        from db.database import async_engine  # type: ignore
        engine = async_engine
    except Exception:
        try:
            from db.database import engine  # type: ignore
        except Exception as exc:
            return {"reachable": False, "error": f"engine import failed: {exc}"}

    # Prefer async path if available
    try:
        from sqlalchemy.ext.asyncio import AsyncEngine  # type: ignore
        if isinstance(engine, AsyncEngine):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"reachable": True}
    except Exception:
        pass

    # Sync fallback — run in thread to avoid blocking event loop
    try:
        import asyncio

        def _sync_ping() -> None:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        await asyncio.to_thread(_sync_ping)
        return {"reachable": True}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


async def _probe_cache() -> Dict[str, Any]:
    try:
        cache = get_cache()
        ok = await cache.ping()
        return {"backend": cache.backend_name, "reachable": ok}
    except Exception as exc:  # pragma: no cover
        return {"backend": "error", "reachable": False, "error": str(exc)}


async def _probe_event_bus() -> Dict[str, Any]:
    try:
        bus = get_event_bus()
        ok = await bus.ping()
        return {"backend": bus.backend_name, "reachable": ok}
    except Exception as exc:  # pragma: no cover
        return {"backend": "error", "reachable": False, "error": str(exc)}


def _probe_scheduler() -> Dict[str, Any]:
    try:
        return {"running": get_scheduler().running}
    except Exception as exc:  # pragma: no cover
        return {"running": False, "error": str(exc)}


@router.get("/health")
async def readiness_check(request: Request):
    """Deep readiness probe — returns 503 when a hard dependency is down."""
    models_status = getattr(request.app.state, "models_loaded", {}) or {}
    models_ok = bool(models_status) and all(models_status.values())

    db_probe = await _probe_db()
    cache_probe = await _probe_cache()
    bus_probe = await _probe_event_bus()
    scheduler_probe = _probe_scheduler()

    # Hard failures: models + db. Soft failures don't toggle 503.
    hard_ok = models_ok and db_probe["reachable"]

    response = {
        "status": "healthy" if hard_ok else "degraded",
        "models": models_status,
        "db": db_probe,
        "cache": cache_probe,
        "event_bus": bus_probe,
        "scheduler": scheduler_probe,
        "gpu_enabled": getattr(request.app.state, "gpu_enabled", False),
        "device": getattr(request.app.state, "device", "unknown"),
    }

    if not hard_ok:
        return JSONResponse(status_code=503, content=response)
    return response
