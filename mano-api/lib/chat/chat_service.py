"""
Enhanced Chat Service — Component 3 Upgrade

Architecture (preserves all existing ML models):
┌─────────────────────────────────────────────────────────────────┐
│ User Message                                                     │
│     │                                                            │
│     ├──► BERT Intent Classifier (PRESERVED — fast, local, free) │
│     │         └── intent + confidence                            │
│     │                                                            │
│     ├──► VADER Sentiment (NEW — local Python lib, unlimited)    │
│     │         └── polarity compound score                        │
│     │                                                            │
│     ├──► GoEmotions (NEW — HuggingFace, ~1K req/day free)       │
│     │         └── fine-grained emotion label                     │
│     │                                                            │
│     ▼                                                            │
│  ROUTING DECISION:                                               │
│     • confidence > 0.7 AND low emotion → Template (fast, free)  │
│     • confidence ≤ 0.7 OR high emotion → Gemini Flash API      │
│     • Gemini unavailable?             → BlenderBot fallback     │
│                                                                  │
│  Crisis Detection runs on EVERY message (PRESERVED)             │
└─────────────────────────────────────────────────────────────────┘

What changed vs. the original:
  + Gemini Flash for complex/emotional messages (free: 15 RPM, 1.5K req/day)
  + VADER sentiment on every message (local, unlimited)
  + GoEmotions emotion label enriches Gemini context (HuggingFace free tier)
  + Session memory: last 10 messages sent as context to Gemini
  + Emotion & sentiment returned in API response

What is PRESERVED (untouched):
  ✓ BERT intent_classifier.py — still does first-pass triage
  ✓ response_generator.py — HybridResponseEngine still used as fallback
  ✓ Crisis detection — still scans every message
  ✓ All database models (ChatSession, ChatMessage)
  ✓ All 3 personas (friend, counselor, medical_officer)
"""

from datetime import datetime
from sqlalchemy.orm import Session
from model.chat_message import ChatMessage, SenderEnum, RoleTypeEnum
from model.chat_session import ChatSession
from ml_models.component3.intent_classifier import IntentClassificationEngine
from ml_models.component3.response_generator import HybridResponseEngine
from lib.CBT.crisis_service import CrisisDetectionService
from lib.chat.gemini_service import gemini_service
from lib.chat.emotion_detector import emotion_detector


class ChatService:
    def __init__(self):
        # 1. Initialize ML Engines (PRESERVED — no changes)
        self.intent_engine = IntentClassificationEngine()
        self.intent_engine.load_model("ml_models/component3")

        # 2. Define Persona Templates (PRESERVED — no changes)
        self.templates = {
            "friend": {
                "greeting": [
                    "Hey! How's it going?",
                    "Hi! I'm here if you want to talk.",
                ],
                "default": ["I'm listening. Tell me more."],
            },
            "counselor": {
                "greeting": [
                    "Hello. How are you feeling today?",
                    "I'm here to support you.",
                ],
                "default": ["That sounds difficult. How does that make you feel?"],
            },
            "medical_officer": {
                "greeting": [
                    "Hello. How can I assist you today?",
                    "I'm here to help with any health concerns.",
                ],
                "default": [
                    "I understand. Could you describe your symptoms in more detail?"
                ],
            },
        }

        # 3. Initialize Response Engine — kept as FALLBACK when Gemini is unavailable
        self.response_engine = HybridResponseEngine(
            responses_dict=self.templates["friend"],
            use_generative=True,
        )

        # 4. Gemini availability flag
        self.gemini_available = gemini_service.is_available

    async def create_session(self, db: Session, user_id: int) -> dict:
        chat_session = ChatSession(
            user_id=user_id,
            title="New Chat",
            created_at=datetime.now()
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        return {
            "session_id": chat_session.id,
            "user_id": user_id,
            "status": "active"
        }

    async def get_all_sessions(self, db: Session, user_id: int):
        """Retrieve all chat sessions for a specific user, including the last message."""
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.created_at.desc()).all()

        result = []
        for session in sessions:
            last_msg = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at.desc())
                .first()
            )
            result.append({
                "session_id": session.id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_message": last_msg.message if last_msg else None,
                "last_message_sender": last_msg.sender.value if last_msg else None,
            })
        return result

    async def get_all_messages_by_session(self, db: Session, session_id: int):
        """Retrieve all chat messages for a specific session."""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).all()
        return [
            {
                "id": msg.id,
                "session_id": msg.session_id,
                "sender": msg.sender.value if msg.sender else None,
                "role_type": msg.role_type.value if msg.role_type else None,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]

    async def delete_session(self, db: Session, session_id: int):
        """Delete a chat session and its associated messages."""
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return False
        db.delete(session)
        db.commit()
        return True

    # ── NEW: Build conversation history for Gemini context window ─────────────

    def _build_conversation_history(self, db: Session, session_id: int, limit: int = 10):
        """
        Fetch last N messages from this session to give Gemini conversational memory.
        Returns list of {role: 'user'|'model', text: str}
        """
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        # Reverse to chronological order
        messages = list(reversed(messages))
        history = []
        for msg in messages:
            role = "user" if msg.sender == SenderEnum.USER else "model"
            history.append({"role": role, "text": msg.message})
        return history

    # ── NEW: Determine if message should route to Gemini ──────────────────────

    def _should_use_gemini(
        self, confidence: float, sentiment_compound: float, emotion_result: dict = None
    ) -> bool:
        """
        Routing logic:
        - Low intent confidence → Gemini (BERT isn't sure what the user wants)
        - High emotional intensity → Gemini (needs empathetic, contextual response)
        - High-confidence known intent → Template/BlenderBot (fast, free)
        """
        if not self.gemini_available:
            return False

        # Low confidence — BERT doesn't know the intent well
        if confidence < 0.7:
            return True

        # Strong negative sentiment — needs empathetic response
        if sentiment_compound <= -0.4:
            return True

        # GoEmotions detected a strong negative emotion
        if emotion_result and emotion_result.get("confidence", 0) > 0.5:
            emotion = emotion_result.get("emotion", "neutral")
            if emotion in ("sadness", "anger", "fear", "disgust"):
                return True

        return False

    # ── ENHANCED: Main message processing ─────────────────────────────────────

    async def process_message(
        self, db: Session, session_id: int, message: str, persona: str
    ) -> dict:
        """
        Processes a chat message with enhanced emotion-aware routing.
        BERT triage → emotion analysis → route to Gemini or template → crisis check.
        """

        # Update session title with first message (PRESERVED)
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if chat_session and chat_session.title == "New Chat":
            chat_session.title = message[:30]

        # 1. Update template engine based on persona (PRESERVED)
        selected_templates = self.templates.get(persona, self.templates["friend"])
        self.response_engine.template_responder.responses = selected_templates

        # 2. BERT intent classification (PRESERVED — fast, local, free)
        intent, confidence = self.intent_engine.predict(message, return_confidence=True)

        # 3. NEW: Emotion & sentiment analysis
        emotion_data = await emotion_detector.full_analysis(message)
        sentiment = emotion_data.get("sentiment", {})
        emotion_result = emotion_data.get("emotion")
        sentiment_compound = sentiment.get("compound", 0.0)

        # 4. NEW: Route to Gemini or fallback
        use_gemini = self._should_use_gemini(confidence, sentiment_compound, emotion_result)
        response_source = "template"  # Track which engine generated the response
        bot_text = None

        if use_gemini:
            # Build session context for Gemini
            conversation_history = self._build_conversation_history(db, session_id)

            # Build user context (assessment scores, risk tier, etc.)
            user_context = {}
            # TODO: Optionally enrich with Component 2 assessment scores
            # This can be wired up once the therapy session service exists

            gemini_response = await gemini_service.generate_response(
                user_message=message,
                persona=persona,
                conversation_history=conversation_history,
                user_context=user_context,
                emotion_label=emotion_result.get("emotion") if emotion_result else None,
                detected_intent=intent,
            )

            if gemini_response:
                bot_text = gemini_response
                response_source = "gemini"

        # 5. Fallback to original hybrid engine if Gemini didn't respond
        if bot_text is None:
            context = {"persona": persona, "topic": intent}
            bot_text = self.response_engine.generate_response(
                user_input=message,
                intent=intent,
                confidence=confidence,
                context=context,
            )
            response_source = "hybrid"

        # 6. Database Persistence (PRESERVED — identical logic)
        role_map = {
            "friend": RoleTypeEnum.FRIEND,
            "counselor": RoleTypeEnum.CONSULTOR,
            "medical_officer": RoleTypeEnum.DOCTOR,
        }
        current_role = role_map.get(persona, RoleTypeEnum.FRIEND)

        user_msg = ChatMessage(
            session_id=session_id,
            sender=SenderEnum.USER,
            role_type=current_role,
            message=message,
            created_at=datetime.now(),
        )
        model_msg = ChatMessage(
            session_id=session_id,
            sender=SenderEnum.MODEL,
            role_type=current_role,
            message=bot_text,
            created_at=datetime.now(),
        )
        db.add_all([user_msg, model_msg])
        db.commit()

        # 7. Crisis Detection Safety Net (PRESERVED — identical logic)
        crisis_result = None
        try:
            user_id = chat_session.user_id if chat_session else None
            if user_id:
                crisis_check = CrisisDetectionService.check_chat_message(
                    db, user_id, message, session_id=session_id
                )
                if crisis_check.get("crisis_detected"):
                    crisis_result = crisis_check
        except Exception:
            pass  # Don't let crisis detection failure break chat

        # 8. Build response (ENHANCED with new fields)
        response = {
            "session_id": session_id,
            "bot_response": bot_text,
            "intent": intent,
            "confidence": round(confidence, 2),
            "persona_used": persona,
            "timestamp": datetime.now().isoformat(),
            # NEW fields — additive, won't break existing frontend
            "response_source": response_source,
            "sentiment": {
                "label": sentiment.get("label", "neutral"),
                "compound": sentiment_compound,
            },
        }

        if emotion_result:
            response["emotion"] = {
                "label": emotion_result.get("emotion", "neutral"),
                "confidence": emotion_result.get("confidence", 0.0),
            }

        if emotion_data.get("intensity"):
            response["emotional_intensity"] = emotion_data["intensity"]

        if crisis_result:
            response["crisis_alert"] = crisis_result

        return response


# Global singleton instance — loaded once on import
chat_service = ChatService()
