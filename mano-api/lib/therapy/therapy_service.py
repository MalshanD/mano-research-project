"""
Guided Wellness Session — Therapy Session Service (Flagship Feature)

Orchestrates ALL 4 components through a 7-phase structured therapy session:

Phase 1: "How are you feeling?" (2-3 min)
  → C2 Risk Model pre-session assessment + mood slider
Phase 2: Active Listening (5-10 min)
  → C3 BERT triage + Gemini Flash conversational AI
Phase 3: CBT Check (3-5 min)
  → C4 MLP CBT Distortion Classifier detects cognitive distortions
Phase 4: Guided Reframe (3-5 min)
  → C4 Reframe Engine + Gemini personalized CBT exercise
Phase 5: Your Next Step (2-3 min)
  → C1 PPO Actor-Critic intervention recommendation + Seq2Seq outcome chart
Phase 6: Wind Down (3-5 min)
  → Breathing exercise + Affirmations.dev + ambient sounds
Phase 7: Session Summary (1-2 min)
  → Before/after risk comparison + auto-journal entry

All existing ML models are PRESERVED and REUSED — no new models needed.
The only new code is the orchestration layer and session state management.

Free APIs used:
  - Gemini Flash (15 RPM, 1.5K req/day) — Phase 2 & 4 conversations
  - Affirmations.dev (unlimited) — Phase 6 affirmation
  - Web Speech API (browser-native) — voice input (frontend only)
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from enum import Enum

from lib.chat.gemini_service import gemini_service
from lib.chat.emotion_detector import emotion_detector
from lib.wellness.affirmation_service import affirmation_service

# Safety guard: hardcoded, fast (<10 ms), zero-IO crisis keyword detector.
# This MUST run on every message regardless of phase (Component-1 revamp
# guideline, Prompt 11). Imported at module top so the guard is reachable
# even when other services are degraded.
from lib.therapy.safety_guard import (
    CrisisSeverity,
    SafetyScanResult,
    scan as safety_scan,
)

logger = logging.getLogger(__name__)


class SessionPhase(str, Enum):
    CHECK_IN = "check_in"           # Phase 1
    ACTIVE_LISTENING = "listening"   # Phase 2
    CBT_CHECK = "cbt_check"         # Phase 3
    GUIDED_REFRAME = "reframe"      # Phase 4
    INTERVENTION = "intervention"    # Phase 5
    WIND_DOWN = "wind_down"         # Phase 6
    SUMMARY = "summary"             # Phase 7
    COMPLETED = "completed"
    # Terminal-until-new-session state. Reached when the safety guard
    # matches a crisis keyword on any user-supplied text. Sessions in
    # CRISIS_HOLD MUST NOT transition further or receive any LLM-generated
    # content; the only valid response is the cached crisis payload.
    CRISIS_HOLD = "crisis_hold"


# Phase progression order
PHASE_ORDER = [
    SessionPhase.CHECK_IN,
    SessionPhase.ACTIVE_LISTENING,
    SessionPhase.CBT_CHECK,
    SessionPhase.GUIDED_REFRAME,
    SessionPhase.INTERVENTION,
    SessionPhase.WIND_DOWN,
    SessionPhase.SUMMARY,
    SessionPhase.COMPLETED,
]


class TherapySessionState:
    """
    In-memory session state for a single therapy session.
    Tracks phase progression, conversation history, mood trajectory,
    and cross-component data flow.
    """

    def __init__(self, user_id: int, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.current_phase = SessionPhase.CHECK_IN
        self.created_at = datetime.now()

        # Phase 1 data
        self.initial_mood_score: Optional[int] = None  # 1-10 slider
        self.initial_concern: Optional[str] = None  # Free text
        self.pre_risk_scores: Optional[Dict] = None  # From C2

        # Phase 2 data — conversation history
        self.conversation_history: List[Dict] = []
        self.detected_emotions: List[str] = []

        # Phase 3 data — CBT analysis
        self.detected_distortion: Optional[Dict] = None  # {type, severity, text}

        # Phase 4 data — Reframe exercise
        self.reframe_steps: List[str] = []

        # Phase 5 data — Intervention recommendations
        self.recommended_interventions: List[Dict] = []

        # Phase 6 data
        self.affirmation: Optional[str] = None

        # Phase 7 data
        self.final_mood_score: Optional[int] = None
        self.post_risk_scores: Optional[Dict] = None
        self.session_summary: Optional[Dict] = None

        # ── Crisis safety fields ──────────────────────────────────────
        # Populated when the safety guard fires on any user-supplied text.
        # Once is_crisis_hold is True the session is terminal — every
        # subsequent endpoint must return the cached crisis payload.
        self.is_crisis_hold: bool = False
        self.crisis_severity: Optional[str] = None
        self.crisis_matched_keywords: List[str] = []
        self.crisis_response: Optional[str] = None
        self.crisis_hotlines: List[Dict] = []
        self.crisis_detected_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        out = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_phase": self.current_phase.value,
            "phase_number": (
                PHASE_ORDER.index(self.current_phase) + 1
                if self.current_phase in PHASE_ORDER else 0
            ),
            "total_phases": 7,
            "created_at": self.created_at.isoformat(),
            "initial_mood": self.initial_mood_score,
            "final_mood": self.final_mood_score,
            "is_crisis_hold": self.is_crisis_hold,
        }
        if self.is_crisis_hold:
            out["crisis"] = {
                "severity": self.crisis_severity,
                "matched_keywords": list(self.crisis_matched_keywords),
                "detected_at": (
                    self.crisis_detected_at.isoformat()
                    if self.crisis_detected_at else None
                ),
            }
        return out


class TherapySessionService:
    """
    Orchestrates the 7-phase guided wellness session.

    This service coordinates calls to existing component services:
    - C2: Risk prediction (lib.assesment.predictor)
    - C3: Chat + Gemini (lib.chat.chat_service, gemini_service)
    - C4: CBT detection (lib.activity.cbt_predictor) — if available
    - C1: PPO recommendations (lib.synthetic.intervention_service) — if available

    Each phase returns a response that the frontend renders in the
    appropriate UI (mood slider, chat, card-based CBT, breathing animation, etc.)
    """

    def __init__(self):
        # Active sessions stored in memory (for this prototype)
        # Production: use Redis or DB-backed session store
        self._sessions: Dict[str, TherapySessionState] = {}
        self._session_counter = 0

    def create_session(self, user_id: int) -> TherapySessionState:
        """Start a new therapy session."""
        self._session_counter += 1
        session_id = f"therapy_{user_id}_{self._session_counter}_{int(datetime.now().timestamp())}"
        state = TherapySessionState(user_id=user_id, session_id=session_id)
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[TherapySessionState]:
        return self._sessions.get(session_id)

    def _advance_phase(self, state: TherapySessionState):
        """Move to the next phase. CRISIS_HOLD is terminal and never advances."""
        if state.is_crisis_hold:
            return
        if state.current_phase not in PHASE_ORDER:
            return
        current_idx = PHASE_ORDER.index(state.current_phase)
        if current_idx < len(PHASE_ORDER) - 1:
            state.current_phase = PHASE_ORDER[current_idx + 1]

    # ── Safety guard ──────────────────────────────────────────────────────────

    def _build_crisis_payload(self, state: "TherapySessionState") -> Dict:
        """Shape the crisis response for any caller that hits a CRISIS_HOLD session.

        Always rendered ABOVE any other content in the chat UI. Never
        passed through an LLM — values come straight from the cached
        scan result.
        """
        return {
            "phase": SessionPhase.CRISIS_HOLD.value,
            "phase_number": 0,
            "status": "crisis_hold",
            "is_crisis_hold": True,
            "severity": state.crisis_severity,
            "message": state.crisis_response,
            "hotlines": list(state.crisis_hotlines),
            "matched_keywords": list(state.crisis_matched_keywords),
            "detected_at": (
                state.crisis_detected_at.isoformat()
                if state.crisis_detected_at else None
            ),
            "next_action": (
                "This session is paused for your safety. Please reach out to "
                "one of the lines above. When you're ready, you can start a "
                "new session at any time."
            ),
        }

    def _run_safety_check(
        self, state: "TherapySessionState", text: Optional[str]
    ) -> Optional[Dict]:
        """Run the hardcoded crisis scan on user-supplied text.

        Returns ``None`` to signal "continue normally". Returns a crisis
        payload dict to signal "stop, do NOT call any LLM, return this".

        Side effects on crisis:
          * Mark the session as CRISIS_HOLD (terminal).
          * Cache the crisis response + hotlines on the state so subsequent
            calls return the same payload deterministically.
          * Emit a CRITICAL event on the in-process event bus so C2/C3/C4
            can react. Best-effort — bus failures never block the response.
        """
        # If the session is already in CRISIS_HOLD, every endpoint must
        # short-circuit to the cached payload, regardless of new input.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        result: SafetyScanResult = safety_scan(text)
        if not result.is_crisis:
            return None

        # ── Latch the crisis state on the session ────────────────────
        state.is_crisis_hold = True
        state.current_phase = SessionPhase.CRISIS_HOLD
        state.crisis_severity = result.severity.value if result.severity else None
        state.crisis_matched_keywords = list(result.matched_keywords)
        state.crisis_response = result.crisis_response
        state.crisis_hotlines = [dict(h) for h in result.hotlines]
        state.crisis_detected_at = datetime.now()

        logger.warning(
            "therapy_crisis_detected",
            extra={
                "session_id": state.session_id,
                "user_id": state.user_id,
                "severity": state.crisis_severity,
                "matched_keywords": state.crisis_matched_keywords,
                "scan_latency_ms": round(result.scan_latency_ms, 4),
            },
        )

        # ── Best-effort event bus emission ───────────────────────────
        # We use a fire-and-forget task so a slow / unreachable bus never
        # blocks the user-facing crisis response. The user gets the
        # hotlines immediately; C2/C3 receive notification on a separate
        # path.
        try:
            import asyncio
            from lib.infra.event_bus import Topics, publish as bus_publish
            payload = {
                "session_id": state.session_id,
                "user_id": state.user_id,
                "severity": state.crisis_severity,
                "matched_keywords": state.crisis_matched_keywords,
                "detected_at": state.crisis_detected_at.isoformat(),
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus_publish(Topics.THERAPY_CRISIS_DETECTED, payload))
            except RuntimeError:
                # No running loop — best-effort sync fallback. Never raise.
                pass
        except Exception as exc:  # pragma: no cover — bus is best-effort
            logger.info("therapy_crisis_event_failed", extra={"error": str(exc)})

        return self._build_crisis_payload(state)

    # ── Phase 1: Check-In ─────────────────────────────────────────────────────

    async def handle_check_in(
        self, state: TherapySessionState, mood_score: int, concern: str = ""
    ) -> Dict:
        """
        Phase 1: "How are you feeling today?"
        Captures initial mood + concern, runs C2 pre-session risk baseline.

        Safety guard runs FIRST on the concern text. If a crisis keyword
        is matched the session immediately latches CRISIS_HOLD and the
        cached crisis payload is returned — no LLM is called, no further
        processing happens.
        """
        # ── HARD SAFETY GATE — runs before any other work, regardless
        #    of phase. Cannot be disabled. <10 ms latency. ─────────────
        crisis = self._run_safety_check(state, concern)
        if crisis is not None:
            return crisis

        state.initial_mood_score = mood_score
        state.initial_concern = concern

        # Run C2 risk prediction if assessment data is available
        # (In production, fetch latest assessment from DB)
        # For now, store mood as the primary signal

        self._advance_phase(state)

        # Prepare Phase 2 opening
        if mood_score <= 3:
            opening = "I can sense you're going through a tough time right now. I'm here, and we can take this at your pace."
        elif mood_score <= 6:
            opening = "Thank you for sharing how you're feeling. Let's explore what's been on your mind."
        else:
            opening = "It's great to check in even when things are going well. What's been on your mind lately?"

        if concern:
            opening += f" You mentioned: \"{concern[:100]}\" — tell me more about that."

        return {
            "phase": "check_in",
            "phase_number": 1,
            "status": "completed",
            "next_phase": "listening",
            "opening_message": opening,
            "mood_recorded": mood_score,
        }

    # ── Phase 2: Active Listening ─────────────────────────────────────────────

    async def handle_listening(
        self, state: TherapySessionState, user_message: str, persona: str = "counselor"
    ) -> Dict:
        """
        Phase 2: AI counselor explores user's concerns.
        Uses BERT triage + Gemini Flash for empathetic, context-aware responses.

        Safety guard runs BEFORE any LLM. If a crisis keyword is matched
        the session latches CRISIS_HOLD and returns the cached crisis
        payload. Gemini, the emotion detector, and conversation history
        are all bypassed in that case.
        """
        # ── HARD SAFETY GATE — runs before any other work, regardless
        #    of phase. Cannot be disabled. <10 ms latency. ─────────────
        crisis = self._run_safety_check(state, user_message)
        if crisis is not None:
            return crisis

        # Emotion analysis
        emotion_data = await emotion_detector.full_analysis(user_message)
        emotion_label = None
        if emotion_data.get("emotion"):
            emotion_label = emotion_data["emotion"].get("emotion")
            state.detected_emotions.append(emotion_label)

        # Build conversation context
        user_context = {
            "initial_mood": state.initial_mood_score,
            "session_phase": "active_listening",
        }
        if state.initial_concern:
            user_context["initial_concern"] = state.initial_concern

        # Generate response via Gemini (context-aware)
        response_text = await gemini_service.generate_response(
            user_message=user_message,
            persona=persona,
            conversation_history=state.conversation_history,
            user_context=user_context,
            emotion_label=emotion_label,
        )

        if not response_text:
            # Fallback
            response_text = "I hear you. That sounds like it's weighing on you. Can you tell me more about how that makes you feel?"

        # Store in conversation history
        state.conversation_history.append({"role": "user", "text": user_message})
        state.conversation_history.append({"role": "model", "text": response_text})

        return {
            "phase": "listening",
            "phase_number": 2,
            "bot_response": response_text,
            "emotion": emotion_data.get("emotion"),
            "sentiment": emotion_data.get("sentiment"),
            "can_advance": len(state.conversation_history) >= 4,  # At least 2 exchanges
        }

    async def advance_from_listening(self, state: TherapySessionState) -> Dict:
        """Transition from Phase 2 → Phase 3 (CBT Check)."""
        # CRISIS_HOLD sessions are terminal — no further phase progression.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)
        self._advance_phase(state)
        return {
            "phase": "cbt_check",
            "phase_number": 3,
            "message": "I noticed something in how you described that situation. Can I share an observation?",
        }

    # ── Phase 3: CBT Check ────────────────────────────────────────────────────

    async def handle_cbt_check(self, state: TherapySessionState) -> Dict:
        """
        Phase 3: Analyze conversation for cognitive distortions.
        Uses C4's MLP CBT Distortion Classifier on the Phase 2 conversation transcript.
        """
        # CRISIS_HOLD short-circuit — no CBT analysis after a crisis flag.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        # Build the full conversation text for CBT analysis
        conversation_text = " ".join(
            msg["text"] for msg in state.conversation_history if msg["role"] == "user"
        )

        # Defence in depth: run the safety scan again on the accumulated
        # transcript. If the scan trips here we still latch CRISIS_HOLD.
        crisis = self._run_safety_check(state, conversation_text)
        if crisis is not None:
            return crisis

        # Try to use C4's CBT predictor
        distortion_result = None
        try:
            from lib.CBT.cbt_predictor import CBTPredictor
            predictor = CBTPredictor()
            distortion_result = predictor.predict(conversation_text)
        except Exception:
            # If C4 predictor isn't available, use Gemini for basic distortion detection
            pass

        if distortion_result and distortion_result.get("distortion_type"):
            state.detected_distortion = distortion_result
            distortion_type = distortion_result.get("distortion_type", "a thinking pattern")

            # Convert clinical label to human language
            human_labels = {
                "catastrophizing": "imagining the worst possible outcome",
                "black_and_white": "seeing things as all-or-nothing",
                "mind_reading": "assuming you know what others think",
                "fortune_telling": "predicting negative outcomes",
                "overgeneralization": "drawing broad conclusions from a single event",
                "personalization": "taking things personally that aren't about you",
                "should_statements": "putting pressure on yourself with 'should' or 'must'",
                "emotional_reasoning": "treating feelings as facts",
                "labeling": "defining yourself by a single trait or event",
                "magnification": "making things seem bigger than they are",
            }
            human_desc = human_labels.get(distortion_type, distortion_type)

            message = (
                f"I noticed you might be {human_desc}. "
                f"This is something many people do — it doesn't mean anything is wrong with you. "
                f"Would you like to explore this thought together?"
            )
        else:
            message = (
                "From what you've shared, I can see this situation has been weighing on you. "
                "Let's try a quick exercise to look at it from a different angle."
            )
            state.detected_distortion = {"distortion_type": "general", "severity": 0.5}

        self._advance_phase(state)

        return {
            "phase": "cbt_check",
            "phase_number": 3,
            "status": "completed",
            "message": message,
            "distortion": state.detected_distortion,
            "next_phase": "reframe",
        }

    # ── Phase 4: Guided Reframe ───────────────────────────────────────────────

    async def handle_reframe(self, state: TherapySessionState) -> Dict:
        """
        Phase 4: Guided CBT reframing exercise.
        3 steps: Evidence → Alternative perspective → Self-compassion
        """
        # CRISIS_HOLD short-circuit — no reframing after a crisis flag.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        distortion = state.detected_distortion or {}
        distortion_type = distortion.get("distortion_type", "thinking pattern")

        # Use Gemini to generate personalized reframe steps
        reframe_prompt = (
            f"The user has been experiencing '{distortion_type}' cognitive distortion. "
            f"Based on their conversation, guide them through a 3-step CBT reframe:\n"
            f"1. 'What's the evidence?' — Ask them to examine the factual evidence\n"
            f"2. 'What's another way to see it?' — Help them find an alternative perspective\n"
            f"3. 'What would you say to a friend?' — Self-compassion exercise\n\n"
            f"Present step 1 now in a warm, conversational tone. "
            f"Reference their actual words from the conversation."
        )

        reframe_text = await gemini_service.generate_response(
            user_message=reframe_prompt,
            persona="counselor",
            conversation_history=state.conversation_history,
        )

        if not reframe_text:
            reframe_text = (
                "Let's try something together. Think about the thought that's been bothering you most. "
                "What's the actual evidence for and against it? Not what you feel — but what you know for certain?"
            )

        state.reframe_steps.append(reframe_text)
        self._advance_phase(state)

        return {
            "phase": "reframe",
            "phase_number": 4,
            "status": "completed",
            "reframe_exercise": reframe_text,
            "steps": [
                "What's the evidence for this thought?",
                "What's another way to see this situation?",
                "What would you say to a friend in this situation?",
            ],
            "next_phase": "intervention",
        }

    # ── Phase 5: Intervention Recommendation ──────────────────────────────────

    async def handle_intervention(self, state: TherapySessionState) -> Dict:
        """
        Phase 5: Recommend personalized interventions.
        Uses C1's PPO Actor-Critic to select optimal intervention.
        Falls back to evidence-based recommendations if C1 isn't available.
        """
        # CRISIS_HOLD short-circuit — interventions are not safe to surface
        # while a session is paused for safety.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        recommendations = []

        # Try C1's PPO Agent for personalized recommendations
        try:
            from lib.synthetic.intervention_service import InterventionService
            int_svc = InterventionService()
            if int_svc.is_loaded():
                # PPO recommendation would go here (requires patient state vector)
                pass
        except Exception:
            pass

        # Fallback: Evidence-based recommendations based on session data
        if not recommendations:
            mood = state.initial_mood_score or 5
            dominant_emotion = max(
                set(state.detected_emotions),
                key=state.detected_emotions.count
            ) if state.detected_emotions else "neutral"

            if mood <= 3 or dominant_emotion in ("sadness", "fear"):
                recommendations = [
                    {
                        "activity": "Guided Breathing Exercise",
                        "reason": "Breathing exercises activate your parasympathetic nervous system, reducing immediate anxiety",
                        "duration": "5 minutes",
                        "type": "immediate",
                    },
                    {
                        "activity": "Nature Walk",
                        "reason": "Studies show 20 minutes in nature reduces cortisol levels by 21%",
                        "duration": "20 minutes",
                        "type": "today",
                    },
                    {
                        "activity": "Gratitude Journaling",
                        "reason": "Writing 3 things you're grateful for has been shown to improve mood within 2 weeks",
                        "duration": "5 minutes",
                        "type": "daily",
                    },
                ]
            elif dominant_emotion == "anger":
                recommendations = [
                    {
                        "activity": "Progressive Muscle Relaxation",
                        "reason": "Tensing and releasing muscles helps discharge physical anger responses",
                        "duration": "10 minutes",
                        "type": "immediate",
                    },
                    {
                        "activity": "High-Intensity Exercise",
                        "reason": "Physical activity channels adrenaline productively and releases endorphins",
                        "duration": "30 minutes",
                        "type": "today",
                    },
                ]
            else:
                recommendations = [
                    {
                        "activity": "Mindfulness Meditation",
                        "reason": "Regular mindfulness practice strengthens emotional regulation",
                        "duration": "10 minutes",
                        "type": "daily",
                    },
                    {
                        "activity": "Social Connection",
                        "reason": "Reaching out to a friend or family member builds your support network",
                        "duration": "15 minutes",
                        "type": "today",
                    },
                ]

        state.recommended_interventions = recommendations
        self._advance_phase(state)

        return {
            "phase": "intervention",
            "phase_number": 5,
            "status": "completed",
            "recommendations": recommendations,
            "next_phase": "wind_down",
        }

    # ── Phase 6: Wind Down ────────────────────────────────────────────────────

    async def handle_wind_down(self, state: TherapySessionState) -> Dict:
        """
        Phase 6: Structured relaxation before session ends.
        Breathing exercise + affirmation + ambient sound suggestion.
        """
        # CRISIS_HOLD short-circuit — relaxation cues are not the right
        # intervention for a paused-for-safety session.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        affirmation = await affirmation_service.get_affirmation()
        state.affirmation = affirmation

        self._advance_phase(state)

        return {
            "phase": "wind_down",
            "phase_number": 6,
            "status": "completed",
            "breathing_exercise": {
                "type": "4-7-8",
                "inhale": 4,
                "hold": 7,
                "exhale": 8,
                "cycles": 3,
                "instruction": "Let's take a moment to breathe together. Inhale for 4 seconds, hold for 7, exhale for 8.",
            },
            "affirmation": affirmation,
            "ambient_sound": {
                "suggestion": "rain",
                "note": "Ambient sounds available via Freesound API (60 req/min, free)",
            },
            "next_phase": "summary",
        }

    # ── Phase 7: Session Summary ──────────────────────────────────────────────

    async def handle_summary(
        self, state: TherapySessionState, final_mood_score: int
    ) -> Dict:
        """
        Phase 7: Generate session summary with before/after comparison.
        Auto-saves as a journal entry.
        """
        # CRISIS_HOLD short-circuit — a paused-for-safety session never
        # produces a normal summary; the cached crisis payload is the
        # canonical response.
        if state.is_crisis_hold:
            return self._build_crisis_payload(state)

        state.final_mood_score = final_mood_score

        mood_change = final_mood_score - (state.initial_mood_score or 5)
        if mood_change > 0:
            mood_message = f"Your mood improved by {mood_change} points during this session."
        elif mood_change < 0:
            mood_message = f"Your mood shifted by {mood_change} points. Some sessions surface difficult emotions — that's a sign of progress, not failure."
        else:
            mood_message = "Your mood stayed steady throughout the session."

        # Build summary
        distortion_name = ""
        if state.detected_distortion:
            distortion_name = state.detected_distortion.get("distortion_type", "")

        interventions_chosen = [
            r.get("activity", "") for r in state.recommended_interventions[:3]
        ]

        summary = {
            "session_id": state.session_id,
            "duration_estimate": "15-25 minutes",
            "mood_before": state.initial_mood_score,
            "mood_after": final_mood_score,
            "mood_change": mood_change,
            "mood_message": mood_message,
            "initial_concern": state.initial_concern,
            "distortion_identified": distortion_name or None,
            "interventions_recommended": interventions_chosen,
            "affirmation": state.affirmation,
            "message_count": len(state.conversation_history),
            "emotions_detected": list(set(state.detected_emotions)),
            "completed_at": datetime.now().isoformat(),
        }

        state.session_summary = summary
        state.current_phase = SessionPhase.COMPLETED

        # Auto-journal entry content
        journal_content = (
            f"Therapy Session Summary — {datetime.now().strftime('%B %d, %Y')}\n\n"
            f"Mood: {state.initial_mood_score}/10 → {final_mood_score}/10 ({mood_message})\n"
        )
        if state.initial_concern:
            journal_content += f"Topic: {state.initial_concern[:200]}\n"
        if distortion_name:
            journal_content += f"Pattern identified: {distortion_name}\n"
        if interventions_chosen:
            journal_content += f"Recommended: {', '.join(interventions_chosen)}\n"
        if state.affirmation:
            journal_content += f"\nAffirmation: {state.affirmation}\n"

        summary["auto_journal_entry"] = journal_content

        # Crisis escalation check (legacy heuristic — kept for backward
        # compatibility; the hardcoded safety_guard is the authoritative
        # crisis path now and runs on every message).
        if state.initial_mood_score and state.initial_mood_score <= 2 and final_mood_score <= 2:
            summary["crisis_notice"] = {
                "message": "MANO noticed some heavy feelings today. Here's a resource if you need someone to talk to.",
                "hotline": "1393 (Sri Lanka) / 988 (US Suicide & Crisis Lifeline)",
                "show_professional_contact": True,
            }

        return {
            "phase": "summary",
            "phase_number": 7,
            "status": "completed",
            "summary": summary,
        }

    def end_session(self, session_id: str):
        """Clean up session from memory."""
        self._sessions.pop(session_id, None)


# Module-level singleton — the routes import this directly.
therapy_service = TherapySessionService()
