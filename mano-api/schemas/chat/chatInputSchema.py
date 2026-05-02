from pydantic import BaseModel
from typing import Optional, Dict
from enum import Enum


class PersonaEnum(str, Enum):
    """Available chat personas."""
    FRIEND = "friend"
    COUNSELOR = "counselor"
    MEDICAL_OFFICER = "medical_officer"


class ChatRequest(BaseModel):
    """Request body for the chat message endpoint."""
    session_id: int
    message: str
    persona: PersonaEnum = PersonaEnum.FRIEND


class SentimentInfo(BaseModel):
    """VADER sentiment polarity."""
    label: str  # "positive", "negative", "neutral"
    compound: float  # -1.0 to 1.0


class EmotionInfo(BaseModel):
    """GoEmotions fine-grained emotion."""
    label: str  # "joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"
    confidence: float  # 0.0 to 1.0


class ChatResponse(BaseModel):
    """Response body returned by the chat message endpoint."""
    session_id: int
    bot_response: str
    intent: str
    confidence: float
    persona_used: str
    timestamp: str
    # NEW — additive fields (all Optional so existing clients don't break)
    response_source: Optional[str] = None  # "template", "gemini", "hybrid"
    sentiment: Optional[SentimentInfo] = None
    emotion: Optional[EmotionInfo] = None
    emotional_intensity: Optional[str] = None  # "low", "moderate", "high"
    crisis_alert: Optional[Dict] = None
