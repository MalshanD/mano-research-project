"""
Integration tests for the therapy safety guard inside ``TherapySessionService``.

These tests verify the **end-to-end** behaviour of the guideline's
"hardcoded safety net" requirement — that the safety guard fires on
every user-supplied text input regardless of phase, latches the session
to ``CRISIS_HOLD``, and that no subsequent handler can resume the
session or invoke the LLM.

Stubbing strategy
-----------------
``TherapySessionService.handle_listening`` calls ``emotion_detector`` and
``gemini_service``. To assert the guard fires *before* either of those
runs (the whole point of the safety net), we monkeypatch both with
recording stubs that raise on call. If the guard works, the stubs are
never invoked. If the guard regresses, the test fails loudly.
"""

from __future__ import annotations

import asyncio

import pytest

from lib.therapy import therapy_service as therapy_service_module
from lib.therapy.therapy_service import (
    SessionPhase,
    TherapySessionService,
    TherapySessionState,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _new_session(svc: TherapySessionService, user_id: int = 42) -> TherapySessionState:
    state = svc.create_session(user_id)
    assert state.current_phase == SessionPhase.CHECK_IN
    assert state.is_crisis_hold is False
    return state


class _ShouldNotBeCalled:
    """Sentinel object that explodes if anything tries to use it.

    Patched onto ``gemini_service`` and ``emotion_detector`` so the test
    fails loudly if the safety guard doesn't short-circuit before LLM
    invocation.
    """

    def __init__(self, label: str) -> None:
        self._label = label

    def __getattr__(self, name: str):  # noqa: D401
        raise AssertionError(
            f"{self._label}.{name} was called during a CRISIS_HOLD path — "
            f"safety guard regression: LLM/detector was invoked after a "
            f"crisis keyword was detected."
        )


@pytest.fixture()
def svc_no_llm(monkeypatch):
    """A fresh service with the LLM and emotion detector booby-trapped.

    Any code path that bypasses the safety guard will hit the trap and
    fail the test.
    """
    monkeypatch.setattr(therapy_service_module, "gemini_service", _ShouldNotBeCalled("gemini_service"))
    monkeypatch.setattr(therapy_service_module, "emotion_detector", _ShouldNotBeCalled("emotion_detector"))
    return TherapySessionService()


# ─── 1. Crisis on Phase-1 concern text latches CRISIS_HOLD ───────────────────


def test_crisis_in_check_in_concern_latches_crisis_hold(svc_no_llm):
    state = _new_session(svc_no_llm)
    result = asyncio.run(
        svc_no_llm.handle_check_in(state, mood_score=4, concern="i want to die tonight")
    )

    # Crisis payload shape
    assert result["is_crisis_hold"] is True
    assert result["phase"] == "crisis_hold"
    assert result["severity"] == "critical"
    assert "want to die" in result["matched_keywords"]
    assert result["hotlines"] and len(result["hotlines"]) >= 3
    assert result["message"]  # non-empty user-facing copy

    # State latched
    assert state.is_crisis_hold is True
    assert state.current_phase == SessionPhase.CRISIS_HOLD
    assert state.crisis_severity == "critical"
    # Crucially: the original mood / concern were NOT recorded — the
    # guard short-circuits before normal field assignment, so a future
    # operator looking at the session state can see this is purely a
    # crisis record, not a half-completed Phase-1 entry.
    assert state.initial_mood_score is None
    assert state.initial_concern is None


# ─── 2. Crisis in a Phase-2 message also latches CRISIS_HOLD ─────────────────


def test_crisis_in_listening_message_latches_crisis_hold(svc_no_llm):
    state = _new_session(svc_no_llm)
    # Manually advance to listening so we test mid-session detection.
    state.current_phase = SessionPhase.ACTIVE_LISTENING
    state.initial_mood_score = 6
    state.initial_concern = "work stress"

    result = asyncio.run(
        svc_no_llm.handle_listening(state, user_message="i feel hopeless and want to hurt myself")
    )

    assert result["is_crisis_hold"] is True
    # Highest tier wins: "hurt myself" is HIGH, "hopeless" is MEDIUM → HIGH.
    assert result["severity"] == "high"
    assert "hurt myself" in result["matched_keywords"]
    assert state.is_crisis_hold is True
    assert state.current_phase == SessionPhase.CRISIS_HOLD

    # Conversation history must NOT be updated on a crisis path —
    # otherwise we'd persist user text to an LLM-bound transcript that
    # never made the round trip.
    assert state.conversation_history == []


# ─── 3. Once CRISIS_HOLD, every subsequent handler returns crisis payload ────


def test_crisis_hold_session_short_circuits_every_subsequent_handler(svc_no_llm):
    state = _new_session(svc_no_llm)
    # Trip the guard.
    asyncio.run(svc_no_llm.handle_check_in(state, mood_score=2, concern="i want to die"))
    assert state.is_crisis_hold is True

    # advance_from_listening → crisis payload
    r = asyncio.run(svc_no_llm.advance_from_listening(state))
    assert r["is_crisis_hold"] is True
    # CBT check → crisis payload
    r = asyncio.run(svc_no_llm.handle_cbt_check(state))
    assert r["is_crisis_hold"] is True
    # Reframe → crisis payload
    r = asyncio.run(svc_no_llm.handle_reframe(state))
    assert r["is_crisis_hold"] is True
    # Intervention recommendations → crisis payload
    r = asyncio.run(svc_no_llm.handle_intervention(state))
    assert r["is_crisis_hold"] is True
    # Wind down → crisis payload
    r = asyncio.run(svc_no_llm.handle_wind_down(state))
    assert r["is_crisis_hold"] is True
    # Summary → crisis payload (mood_score ignored — session is terminal)
    r = asyncio.run(svc_no_llm.handle_summary(state, final_mood_score=8))
    assert r["is_crisis_hold"] is True

    # Phase never advances out of CRISIS_HOLD.
    assert state.current_phase == SessionPhase.CRISIS_HOLD


# ─── 4. Re-sending text on a CRISIS_HOLD session is also short-circuited ─────


def test_crisis_hold_blocks_new_message_without_re_invoking_llm(svc_no_llm):
    state = _new_session(svc_no_llm)
    asyncio.run(svc_no_llm.handle_check_in(state, mood_score=2, concern="i want to die"))

    # User sends a follow-up that on its own is benign — it must still
    # be short-circuited because the session is terminal.
    r = asyncio.run(
        svc_no_llm.handle_listening(state, user_message="thank you for the resources")
    )
    assert r["is_crisis_hold"] is True
    assert r["severity"] == "critical"  # original severity is preserved
    # Booby-trapped LLM/emotion stubs were never invoked — if they had
    # been, this test would already have failed via _ShouldNotBeCalled.


# ─── 5. Benign session flow does NOT latch crisis ────────────────────────────


@pytest.fixture()
def svc_benign(monkeypatch):
    """Service with cooperative stubs for the benign-flow test.

    handle_listening does run when the message is benign, so we need
    real-shaped stubs (returning dicts / strings) instead of trap stubs.
    """

    class _StubEmotion:
        async def full_analysis(self, _text):
            return {"emotion": {"emotion": "calm"}, "sentiment": {"score": 0.5}}

    class _StubGemini:
        async def generate_response(self, **_kwargs):
            return "I hear you. Tell me more about that."

    monkeypatch.setattr(therapy_service_module, "emotion_detector", _StubEmotion())
    monkeypatch.setattr(therapy_service_module, "gemini_service", _StubGemini())
    return TherapySessionService()


def test_benign_check_in_and_listening_does_not_trip_safety_guard(svc_benign):
    state = svc_benign.create_session(user_id=1)
    r1 = asyncio.run(
        svc_benign.handle_check_in(state, mood_score=6, concern="just a stressful day at work")
    )
    assert r1.get("is_crisis_hold") is not True
    assert state.is_crisis_hold is False
    assert state.current_phase == SessionPhase.ACTIVE_LISTENING
    assert state.initial_mood_score == 6
    assert state.initial_concern == "just a stressful day at work"

    r2 = asyncio.run(
        svc_benign.handle_listening(state, user_message="my deadline is tight but I'm coping")
    )
    assert r2.get("is_crisis_hold") is not True
    assert state.is_crisis_hold is False
    # Conversation history grew normally
    assert len(state.conversation_history) == 2
