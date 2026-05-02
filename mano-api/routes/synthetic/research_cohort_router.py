"""
Researcher Cohort router.

Endpoints
---------
* ``POST /generate``                          — generate a new synthetic cohort.
* ``GET  /``                                  — list all cohorts (newest first).
* ``GET  /{cohort_id}``                       — fetch a cohort manifest.
* ``GET  /{cohort_id}/download/{filename}``   — stream one of the cohort's files.

Why a dedicated "research" prefix?
----------------------------------
The existing ``/api/v1/twin`` factory is for the clinical frontend — it
bundles a digital twin with weather modulation etc. The research endpoints
here are plain synthetic data export: no environment modulation, no
orchestration, just CTGAN + TimeGAN with a reproducibility manifest. That
separation keeps audit trails clean — we can tell exactly which calls were
research exports vs. clinical twin generation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from lib.synthetic.research_cohort_service import (
    generate_cohort,
    list_cohorts,
    load_manifest,
    resolve_cohort_file,
)
from schemas.synthetic.research_cohort_schema import (
    CohortGenerateRequest,
    CohortGenerateResponse,
    CohortListResponse,
    CohortManifest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=CohortGenerateResponse)
async def generate(request: CohortGenerateRequest) -> CohortGenerateResponse:
    try:
        return await generate_cohort(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cohort_generate_failed")
        raise HTTPException(
            status_code=500, detail=f"Cohort generation failed: {exc}",
        ) from exc


@router.get("/", response_model=CohortListResponse)
async def list_all() -> CohortListResponse:
    cohorts = list_cohorts()
    return CohortListResponse(count=len(cohorts), cohorts=cohorts)


@router.get("/{cohort_id}", response_model=CohortManifest)
async def get_manifest(cohort_id: str) -> CohortManifest:
    try:
        return load_manifest(cohort_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Cohort '{cohort_id}' not found.",
        ) from exc


@router.get("/{cohort_id}/download/{filename}")
async def download_file(cohort_id: str, filename: str) -> FileResponse:
    try:
        path = resolve_cohort_file(cohort_id, filename)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"File '{filename}' not found for cohort '{cohort_id}'.",
        ) from exc

    suffix = Path(filename).suffix.lower()
    media_type = {
        ".csv": "text/csv",
        ".jsonl": "application/x-ndjson",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")
    return FileResponse(path=str(path), media_type=media_type, filename=filename)
