from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from db.base import Base
from datetime import datetime


class ActivityFeedback(Base):
    """Stores user feedback on completed activities.
    Used to build an effectiveness feedback loop —
    activities that genuinely help users get boosted in future recommendations."""
    __tablename__ = "activity_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(String(50), nullable=False, index=True)

    # 1-5 star effectiveness rating
    effectiveness_rating = Column(Integer, nullable=False)  # 1=not helpful, 5=very helpful

    # Mood before and after (optional, 1-5 scale)
    mood_before = Column(Integer, nullable=True)  # 1=very bad, 5=very good
    mood_after = Column(Integer, nullable=True)    # 1=very bad, 5=very good

    # Optional text note
    feedback_note = Column(Text, nullable=True)

    # Would recommend to others?
    would_recommend = Column(Integer, nullable=True)  # 1=no, 2=maybe, 3=yes

    created_at = Column(DateTime, default=datetime.now)
