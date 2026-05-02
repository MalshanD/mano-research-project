"""
Researcher Cohort — Privacy & Utility Audit router.

Endpoint
--------
* ``POST /cohort`` — audit a previously-generated cohort.

Purposefully stateless: the audit result is NOT persisted. Researchers
re-run the audit when they change ``quasi_identifiers`` or ``k_min``.
If we ever need an audit trail, the event bus is a better place for it
than adding a sidecar file per audit.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.synthetic.research_audit_service import audit_cohort
from schemas.synthetic.research_audit_schema import (
    CohortAuditRequest,
    CohortAuditResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/cohort", response_model=CohortAuditResponse)
async def audit(request: CohortAuditRequest) -> CohortAuditResponse:
    try:
        return audit_cohort(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Cohort not found: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cohort_audit_failed")
        raise HTTPException(
            status_code=500, detail=f"Audit failed: {exc}",
        ) from exc
