"""HTTP route layer for the Outcome Attribution Engine.

Single endpoint that decomposes an observed/projected delta-risk into
the causal intervention effect plus baseline drift, via a Seq2Seq null
counterfactual.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from core.errors import ErrorCode, MANOAPIError
from lib.synthetic import attribution_service
from schemas.synthetic.attribution_schema import (
    AttributionReport,
    AttributionRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/explain",
    response_model=AttributionReport,
    summary="Decompose projected risk change into intervention effect + baseline drift",
    description=(
        "Given a patient state and the intervention they actually took, "
        "project two arms (the chosen intervention vs. a null Control "
        "arm) through Seq2Seq + LSTM and decompose the observed change "
        "into the causal intervention effect plus what would have "
        "happened anyway. Powers the 'how much of my improvement is "
        "really from this plan?' UX."
    ),
)
async def explain_outcome(request: AttributionRequest) -> AttributionReport:
    try:
        return attribution_service.attribute_outcome(request)
    except RuntimeError as exc:
        logger.error("attribution_model_unavailable", extra={"error": str(exc)})
        raise MANOAPIError(
            code=ErrorCode.MODEL_UNAVAILABLE,
            message=(
                "A frozen Component-1 model required for outcome "
                "attribution is not loaded. Check /health."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
