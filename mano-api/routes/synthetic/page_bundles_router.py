"""HTTP route layer for the consumer-facing page-bundle aggregator.

Six endpoints, one per consumer-facing page from the navigation
restructure. Each returns the full payload the page binds to — the
frontend issues exactly ONE request per page, not five.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, Query

from lib.synthetic import page_bundles_service
from schemas.synthetic.page_bundles_schema import (
    AIRecommendationBundle,
    DigitalTwinBundle,
    GuidedTherapyEntryBundle,
    MySummaryBundle,
    SeeMyFutureBundle,
    UnderstandMyRiskBundle,
)
from schemas.synthetic.simulation_schema import InterventionType, PatientState
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class _SummaryRequest(BaseModel):
    patient_id: str
    patient_state: PatientState
    user_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


@router.post(
    "/summary/bundle",
    response_model=MySummaryBundle,
    summary="My Summary page — single-fetch bundle",
)
async def my_summary_bundle(payload: _SummaryRequest) -> MySummaryBundle:
    return page_bundles_service.my_summary_bundle(
        patient_id=payload.patient_id,
        patient_state=payload.patient_state,
        user_name=payload.user_name,
        lat=payload.lat,
        lon=payload.lon,
    )


class _SeeMyFutureRequest(BaseModel):
    patient_state: PatientState
    lat: Optional[float] = None
    lon: Optional[float] = None
    arms: Optional[list[InterventionType]] = None


@router.post(
    "/see-my-future/preview",
    response_model=SeeMyFutureBundle,
    summary="See My Future — pre-filled with weather, three projections + narratives",
)
async def see_my_future_preview(payload: _SeeMyFutureRequest) -> SeeMyFutureBundle:
    return page_bundles_service.see_my_future_bundle(
        patient_state=payload.patient_state,
        lat=payload.lat,
        lon=payload.lon,
        arms=payload.arms,
    )


class _RecommendationRequest(BaseModel):
    patient_state: PatientState
    prefill_arm: Optional[InterventionType] = None


@router.post(
    "/recommendation/bundle",
    response_model=AIRecommendationBundle,
    summary="AI Recommendation — three ranked plans with evidence + narratives",
)
async def ai_recommendation_bundle(payload: _RecommendationRequest) -> AIRecommendationBundle:
    return page_bundles_service.ai_recommendation_bundle(
        patient_state=payload.patient_state,
        prefill_arm=payload.prefill_arm,
    )


@router.get(
    "/digital-twin/bundle",
    response_model=DigitalTwinBundle,
    summary="Digital Twin — onboarding + privacy promises",
)
async def digital_twin_bundle() -> DigitalTwinBundle:
    return page_bundles_service.digital_twin_bundle()


class _UnderstandMyRiskRequest(BaseModel):
    patient_state: PatientState


@router.post(
    "/understand-my-risk/bundle",
    response_model=UnderstandMyRiskBundle,
    summary="Understand My Risk — plain-English XAI with optional SHAP toggle",
)
async def understand_my_risk_bundle(payload: _UnderstandMyRiskRequest) -> UnderstandMyRiskBundle:
    return page_bundles_service.understand_my_risk_bundle(payload.patient_state)


@router.get(
    "/guided-therapy/bundle",
    response_model=GuidedTherapyEntryBundle,
    summary="Guided Therapy entry — phase strip + safety promise",
)
async def guided_therapy_bundle() -> GuidedTherapyEntryBundle:
    return page_bundles_service.guided_therapy_entry_bundle()


class _FeedbackRequest(BaseModel):
    patient_id: str
    intervention_type: int
    feedback: str
    context: dict = {}

@router.post(
    "/feedback/intervention",
    summary="Record user feedback for an intervention arm",
)
async def record_intervention_feedback(payload: _FeedbackRequest):
    logger.info("recorded_intervention_feedback", patient_id=payload.patient_id, intervention_type=payload.intervention_type, feedback=payload.feedback)
    return {"status": "success", "recorded": True}
