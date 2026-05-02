"""
Clinical Passport router.

Endpoints
---------
* ``POST /generate`` — render a passport PDF from a composed payload.
* ``GET /file/{passport_id}`` — stream a previously-rendered PDF back.

The passport generator is a pass-through renderer — see
``lib/synthetic/clinical_passport_service.py`` for the rationale. Upstream
services (dashboard aggregator, care-path orchestrator, reranker, narrative,
evidence) stitch live signals together and hand the packaged payload to
this endpoint.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from lib.synthetic.clinical_passport_service import (
    generate_passport,
    resolve_passport_path,
)
from schemas.synthetic.clinical_passport_schema import (
    ClinicalPassportRequest,
    ClinicalPassportResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=ClinicalPassportResponse)
async def generate(request: ClinicalPassportRequest) -> ClinicalPassportResponse:
    try:
        return await generate_passport(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("passport_generation_failed")
        raise HTTPException(
            status_code=500, detail=f"Passport generation failed: {exc}",
        ) from exc


@router.get("/file/{passport_id}")
async def download(passport_id: str) -> FileResponse:
    try:
        path = resolve_passport_path(passport_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Passport '{passport_id}' not found.") from exc
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"mano_passport_{passport_id}.pdf",
    )
