"""
Narrative v2 router — Future-Self journal endpoint.

Thin HTTP wrapper over ``lib/synthetic/narrative_v2_service.py``. The service
never raises on provider failure — it returns a ``fallback`` result — so this
route is small and boring by design.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from lib.synthetic.narrative_v2_service import generate_narrative
from schemas.synthetic.narrative_schema import (
    NarrativeRequest,
    NarrativeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/future_self", response_model=NarrativeResponse)
async def future_self_narrative(request: NarrativeRequest) -> NarrativeResponse:
    """Generate a Future-Self journal entry from a trajectory summary.

    Accepts a trajectory summary (shape, peak-risk day, mean high-risk
    probability) rather than raw vitals — this keeps the narrative grounded
    in what the Seq2Seq + LSTM actually predicted instead of re-inferring.
    """
    result = await generate_narrative(
        trajectory=request.trajectory,
        tone=request.tone,
        length=request.length,
        patient_voice=request.patient_voice,
    )
    return NarrativeResponse(
        narrative=result.narrative,
        intervention=request.trajectory.intervention,
        tone=request.tone,
        length=request.length,
        source=result.source,
        provider=result.provider,
        notes=result.notes,
    )
