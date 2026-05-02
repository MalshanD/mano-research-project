"""
Guided Wellness Session API — Therapy Session Routes

The flagship feature: a structured, multi-phase therapy session that
orchestrates all 4 MANO components into a cohesive counselor-like experience.

Endpoints:
  POST /api/v1/therapy/start          — Start a new session
  GET  /api/v1/therapy/{id}/status    — Get session state
  POST /api/v1/therapy/{id}/check-in  — Phase 1: mood + concern
  POST /api/v1/therapy/{id}/message   — Phase 2: active listening exchange
  POST /api/v1/therapy/{id}/advance   — Move from listening → CBT check
  GET  /api/v1/therapy/{id}/cbt       — Phase 3: CBT distortion analysis
  GET  /api/v1/therapy/{id}/reframe   — Phase 4: guided reframe exercise
  GET  /api/v1/therapy/{id}/plan      — Phase 5: intervention recommendations
  GET  /api/v1/therapy/{id}/relax     — Phase 6: wind down
  POST /api/v1/therapy/{id}/complete  — Phase 7: summary + auto-journal
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from lib.therapy.therapy_service import therapy_service

router = APIRouter(prefix="/api/v1/therapy", tags=["Guided Wellness Session"])


class StartSessionRequest(BaseModel):
    user_id: int


class CheckInRequest(BaseModel):
    mood_score: int = Field(ge=1, le=10, description="Mood on a 1-10 scale")
    concern: Optional[str] = Field(default="", max_length=500, description="What's on your mind?")


class MessageRequest(BaseModel):
    message: str = Field(max_length=2000)
    persona: Optional[str] = "counselor"


class CompleteRequest(BaseModel):
    final_mood_score: int = Field(ge=1, le=10, description="Post-session mood 1-10")


@router.post("/start", status_code=status.HTTP_201_CREATED, summary="Start a guided wellness session")
async def start_session(request: StartSessionRequest):
    state = therapy_service.create_session(request.user_id)
    return {
        "session_id": state.session_id,
        "message": "Welcome to your guided wellness session. Let's start by checking in — how are you feeling right now?",
        "current_phase": "check_in",
        "phase_number": 1,
        "total_phases": 7,
    }


@router.get("/{session_id}/status", summary="Get session status")
async def get_session_status(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state.to_dict()


@router.post("/{session_id}/check-in", summary="Phase 1: Record mood and initial concern")
async def check_in(session_id: str, request: CheckInRequest):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_check_in(state, request.mood_score, request.concern)
    return result


@router.post("/{session_id}/message", summary="Phase 2: Send a message during active listening")
async def send_message(session_id: str, request: MessageRequest):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_listening(state, request.message, request.persona)
    return result


@router.post("/{session_id}/advance", summary="Advance from active listening to CBT check")
async def advance_phase(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.advance_from_listening(state)
    return result


@router.get("/{session_id}/cbt", summary="Phase 3: CBT distortion analysis")
async def cbt_check(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_cbt_check(state)
    return result


@router.get("/{session_id}/reframe", summary="Phase 4: Guided CBT reframe exercise")
async def reframe(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_reframe(state)
    return result


@router.get("/{session_id}/plan", summary="Phase 5: Personalized intervention recommendations")
async def intervention_plan(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_intervention(state)
    return result


@router.get("/{session_id}/relax", summary="Phase 6: Wind down with breathing + affirmation")
async def wind_down(session_id: str):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_wind_down(state)
    return result


@router.post("/{session_id}/complete", summary="Phase 7: Session summary + auto-journal entry")
async def complete_session(session_id: str, request: CompleteRequest):
    state = therapy_service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await therapy_service.handle_summary(state, request.final_mood_score)
    return result
