import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Date
from db.base import Base
from datetime import datetime


class MoodType(enum.Enum):
    great = "great"
    good = "good"
    okay = "okay"
    low = "low"
    bad = "bad"


class MoodCheckIn(Base):
    __tablename__ = "mood_checkin"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mood = Column(Enum(MoodType), nullable=False)
    checkin_date = Column(Date, nullable=False)  # One check-in per user per day
    created_at = Column(DateTime, default=datetime.now)
