"""
Adaptive Intervention Rehearsal — HTTP route layer.

Single endpoint that runs the closed-loop rehearsal engine and returns a
fully-shaped ``RehearsalPlan``. See ``lib/synthetic/rehearsal_service.py``
for the algorithm.

Why one endpoint, not three. The earlier scaffolding splits "predict",
"prescribe", "simulate", "compare" across separate endpoints that each
do one model call. The rehearsal engine does the *whole* loop in one
call because the loop's value is the loop — splitting it back into
single-model steps would just rebuild the existing one-shot routes
under a new prefix. We keep the surface tight: one call returns one
plan, with all the day-by-day detail the frontend needs to render
charts, swap timelines, and confidence bands.

Cost. ~1.5 s end-to-end on the RTX 3050 Ti budget for a 14-day plan with
three adherence branches and one MC Dropout band; well within the
``RATE_LIMIT_ML`` budget.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from core.errors import ErrorCode, MANOAPIError
from lib.synthetic import rehearsal_service
from schemas.synthetic.rehearsal_schema import RehearsalPlan, RehearsalRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/plan",
    response_model=RehearsalPlan,
    summary="Run the adaptive intervention rehearsal engine for one patient",
    description=(
        "Closed-loop multi-day rehearsal that composes all five frozen C1 "
        "models (CTGAN, TimeGAN, Hybrid LSTM, PPO, Seq2Seq + MC Dropout) "
        "to produce a personalized day-by-day plan with realistic "
        "adherence projections, mid-plan swap recommendations, and "
        "confidence bands. Returns three trajectories (pessimistic / "
        "realistic / optimistic) over the requested horizon."
    ),
)
async def rehearse_plan(request: RehearsalRequest) -> RehearsalPlan:
    try:
        return rehearsal_service.rehearse_plan(request)
    except ValueError as exc:
        # Misshaped input — e.g. missing patient_state without
        # synthesize_missing_data. Surface as a structured 400.
        raise MANOAPIError(
            code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    except RuntimeError as exc:
        # Frozen model not loaded.
        logger.error("rehearsal_model_unavailable", extra={"error": str(exc)})
        raise MANOAPIError(
            code=ErrorCode.MODEL_UNAVAILABLE,
            message=(
                "One of the frozen Component-1 models required for the "
                "rehearsal engine is not loaded. Check /health for status."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
