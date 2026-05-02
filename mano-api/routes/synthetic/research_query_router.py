"""
Researcher Cohort — Aggregate Query router.

Endpoint
--------
* ``POST /query`` — run an aggregate query (filter + group-by + aggregate)
  against a stored cohort. Never returns individual rows; groups smaller
  than ``k_min`` are suppressed.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.synthetic.research_query_service import query_cohort
from schemas.synthetic.research_query_schema import (
    CohortQueryRequest,
    CohortQueryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=CohortQueryResponse)
async def query(request: CohortQueryRequest) -> CohortQueryResponse:
    try:
        return query_cohort(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Cohort not found: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cohort_query_failed")
        raise HTTPException(
            status_code=500, detail=f"Query failed: {exc}",
        ) from exc
