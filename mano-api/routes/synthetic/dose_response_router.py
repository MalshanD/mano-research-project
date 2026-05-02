"""HTTP route layer for the Dose-Response Sweep Engine.

Sweeps the intensity axis for one intervention type and returns the
dose-response curve plus the patient's personal "sweet spot" — the
lowest intensity past which the marginal benefit flattens. Powers the
"how much effort do I need?" UX.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from core.errors import ErrorCode, MANOAPIError
from lib.synthetic import dose_response_service
from schemas.synthetic.dose_response_schema import (
    DoseResponseCurve,
    DoseResponseRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/sweep",
    response_model=DoseResponseCurve,
    summary="Sweep intervention intensity and return the dose-response curve",
    description=(
        "For a single intervention type, projects the patient's 7-14 "
        "day trajectory at each intensity in the dose grid and returns "
        "(a) projected high-risk probability per dose, (b) the marginal "
        "Δrisk per step, and (c) the personal sweet-spot intensity "
        "(None if the curve is monotonically improving). Powers the "
        "'how much is enough?' UX over PPO's single-point optimum."
    ),
)
async def sweep_dose_response(request: DoseResponseRequest) -> DoseResponseCurve:
    try:
        return dose_response_service.sweep_dose_response(request)
    except ValueError as exc:
        raise MANOAPIError(
            code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    except RuntimeError as exc:
        logger.error("dose_response_model_unavailable", extra={"error": str(exc)})
        raise MANOAPIError(
            code=ErrorCode.MODEL_UNAVAILABLE,
            message=(
                "A frozen Component-1 model required for the dose-response "
                "engine is not loaded. Check /health."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
