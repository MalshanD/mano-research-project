"""
PubMed Evidence (v2) router.

Two entry points:

* ``POST /for_intervention`` — curated-term lookup by intervention keyword.
* ``GET /search``            — free-form search-term lookup.

Both share the same underlying service + cache, so a free-form query for
``"mindfulness anxiety"`` will warm-populate a cache row that the curated
lookup for ``meditation`` would miss. This is intentional — researchers
(Component 4) want the free-form surface.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from lib.synthetic.evidence_service import fetch_evidence
from schemas.synthetic.evidence_schema import (
    EvidenceCard,
    EvidenceRequest,
    EvidenceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _response(payload: dict) -> EvidenceResponse:
    return EvidenceResponse(
        intervention=payload["intervention"],
        cards=[EvidenceCard(**c) for c in payload.get("cards", [])],
        source=payload["source"],
        provider=payload.get("provider", "pubmed"),
        cache_key=payload.get("cache_key"),
        notes=payload.get("notes", []),
    )


@router.post("/for_intervention", response_model=EvidenceResponse)
async def for_intervention(request: EvidenceRequest) -> EvidenceResponse:
    """Return PubMed evidence cards for a named intervention."""
    payload = await fetch_evidence(
        request.intervention,
        max_results=request.max_results,
        include_abstract=request.include_abstract,
    )
    return _response(payload)


@router.get("/search", response_model=EvidenceResponse)
async def search(
    term: str = Query(..., min_length=2, max_length=200),
    max_results: int = Query(3, ge=1, le=10),
    include_abstract: bool = Query(True),
) -> EvidenceResponse:
    """Free-form PubMed search — same cache as /for_intervention."""
    payload = await fetch_evidence(
        term, max_results=max_results, include_abstract=include_abstract
    )
    return _response(payload)
