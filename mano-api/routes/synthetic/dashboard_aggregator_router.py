"""
Dashboard Intelligence router.

``POST /summary`` is the only endpoint — the client sends whatever context
it has (trajectory, city, sentiment, dominant emotion, etc.) and the
aggregator returns a per-panel response with health envelopes.

The aggregator is stateless. It doesn't know about patient identity; the
caller composes the request from its own authenticated session.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.synthetic.dashboard_service import build_dashboard
from schemas.synthetic.dashboard_schema import DashboardRequest, DashboardResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/summary", response_model=DashboardResponse)
async def summary(request: DashboardRequest) -> DashboardResponse:
    try:
        return await build_dashboard(request)
    except Exception as exc:  # pragma: no cover — build_dashboard never raises
        logger.exception("dashboard_failed")
        raise HTTPException(status_code=500, detail=f"Dashboard failed: {exc}") from exc
