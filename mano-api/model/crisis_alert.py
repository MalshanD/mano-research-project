import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum
from db.base import Base
from datetime import datetime


class CrisisSeverity(enum.Enum):
    low = "low"            # Concerning language but ambiguous
    medium = "medium"      # Clear distress signals
    high = "high"          # Explicit crisis language
    critical = "critical"  # Imminent danger signals


class CrisisSource(enum.Enum):
    chat_message = "chat_message"      # Detected from chat keywords/intent
    mood_pattern = "mood_pattern"      # Consecutive bad/low moods
    engagement_drop = "engagement_drop"  # Sudden stop in activity
    post_content = "post_content"      # Crisis language in community post
    manual = "manual"                  # Manually flagged


class CrisisAlert(Base):
    """Logs detected crisis events for user safety tracking."""
    __tablename__ = "crisis_alert"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    severity = Column(Enum(CrisisSeverity), nullable=False)
    source = Column(Enum(CrisisSource), nullable=False)
    trigger_text = Column(Text, nullable=True)  # The text that triggered (first 200 chars)
    details = Column(Text, nullable=True)  # JSON-encoded details about the detection
    is_active = Column(Boolean, default=True, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
