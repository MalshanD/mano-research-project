"""HTTP route layer for the Future-Self Narrative engine.

Two endpoints — single narrative and a batched parallel-futures
narrative for "compare three plans side-by-side" UX.

The existing ``/api/v1/narrative/future_self`` route lives in a
sibling module that wraps the older v1 service. This new router lives
under ``/api/v1/future-self`` to avoid colliding with that path while
the consolidation lands.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from lib.synthetic import future_self_service
from schemas.synthetic.future_self_schema import (
    FutureSelfNarrative,
    FutureSelfRequest,
    ParallelFuturesRequest,
    ParallelFuturesResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/narrative",
    response_model=FutureSelfNarrative,
    summary="Single first-person Day-7 narrative for one Seq2Seq projection",
)
async def future_self_narrative(request: FutureSelfRequest) -> FutureSelfNarrative:
    return future_self_service.generate_future_self(request)


@router.post(
    "/parallel-futures",
    response_model=ParallelFuturesResponse,
    summary="Batched narratives for 2–3 candidate plans",
    description=(
        "Single Groq call produces narratives for every supplied "
        "projection (one per scenario). Falls back to deterministic "
        "templates if Groq is unavailable. Use for the 'compare plans' "
        "card stack on the AI Recommendation page."
    ),
)
async def parallel_futures(request: ParallelFuturesRequest) -> ParallelFuturesResponse:
    return future_self_service.generate_parallel_futures(request)
