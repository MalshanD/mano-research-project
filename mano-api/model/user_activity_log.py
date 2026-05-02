from sqlalchemy import Column, Integer, Boolean, ForeignKey, Date, DateTime
from db.base import Base
from datetime import datetime


class UserActivityLog(Base):
    """Tracks daily engagement per user. One row per user per day.
    Used for streak calculation and badge awarding."""
    __tablename__ = "user_activity_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)

    # Counters for different engagement types
    activities_completed = Column(Integer, default=0)
    posts_created = Column(Integer, default=0)
    mood_checked_in = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
