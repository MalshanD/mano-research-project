"""
Care-Path Therapy Orchestrator router.

Endpoints:

* ``POST /transition`` — process a snapshot, return the (possibly
  transitioned) state and downstream guidance.
* ``GET /state/{patient_id}`` — read-only view of the stored state.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.synthetic.therapy_orchestrator_service import (
    get_state,
    transition,
)
from schemas.synthetic.therapy_orchestrator_schema import (
    CarePathState,
    PhaseTransitionRequest,
    PhaseTransitionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transition", response_model=PhaseTransitionResponse)
async def process_snapshot(request: PhaseTransitionRequest) -> PhaseTransitionResponse:
    try:
        result = await transition(request.snapshot)
    except Exception as exc:  # pragma: no cover — transition never raises
        logger.exception("therapy_transition_failed")
        raise HTTPException(
            status_code=500, detail=f"Therapy transition failed: {exc}",
        ) from exc

    return PhaseTransitionResponse(
        state=result["state"],
        transitioned=result["transitioned"],
        phase_guidance=result["phase_guidance"],
        recommended_intervention_tones=result["recommended_intervention_tones"],
        review_cadence_days=result["review_cadence_days"],
        safety_escalation_required=result["safety_escalation_required"],
    )


@router.get("/state/{patient_id}", response_model=CarePathState)
async def read_state(patient_id: str) -> CarePathState:
    state = await get_state(patient_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No care-path state for '{patient_id}'.")
    return state
