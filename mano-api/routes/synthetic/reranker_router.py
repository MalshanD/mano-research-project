"""
PPO Reranker router.

A second-pass ranker that sits alongside the existing
``/api/v1/nba/recommend`` endpoint. The NBA endpoint already returns the
simulator's best single pick; this endpoint returns a *ranked list* with
explicit weight-vector blending so clinicians can see WHY a candidate
rose or fell relative to the PPO's unblended choice.

Endpoint:

* ``POST /rerank`` — blend PPO policy probability, simulator risk
  reduction, adherence prior, care-phase prior and patient preferences
  into a final ranking.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from lib.synthetic.reranker_service import rerank
from schemas.synthetic.reranker_schema import (
    RerankerRequest,
    RerankerResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/rerank", response_model=RerankerResponse)
async def rerank_endpoint(request: RerankerRequest) -> RerankerResponse:
    """Rerank the intervention action space for a given patient snapshot.

    The response always includes:

    * ``ppo_top_pick`` — what the frozen PPO picked on its own, *before*
      the reranker blends in the other axes. This is the audit anchor.
    * ``weights`` — the exact blend weights used (echoed back so the UI
      and logs show what the service actually applied, including any
      normalisation).
    * ``candidates`` — ranked list trimmed to ``top_k``.
    * ``blocked`` — interventions removed by contraindication, surfaced
      so clinicians can see *why* something is missing.
    * ``agreement_with_ppo`` — quick flag for dashboards: does the blend
      agree with the model's raw preference?
    """
    try:
        return await rerank(request)
    except ValueError as exc:
        # Weight-vector validation, contraindication parsing, etc.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("reranker_failed")
        raise HTTPException(
            status_code=500, detail=f"Reranker failed: {exc}",
        ) from exc
