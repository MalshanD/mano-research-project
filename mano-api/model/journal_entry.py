"""CBT Thought Journal — database model for journal entries with distortion analysis."""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Date, Boolean
from db.base import Base
from datetime import datetime


class JournalEntry(Base):
    __tablename__ = "journal_entry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # User's journal text
    entry_text = Column(Text, nullable=False)
    entry_date = Column(Date, nullable=False, index=True)

    # ML analysis results (stored after classification)
    distortion_type = Column(String(50), nullable=True)         # e.g. "catastrophizing", "none"
    distortion_label = Column(String(100), nullable=True)       # e.g. "Catastrophizing"
    confidence = Column(Float, nullable=True)                   # 0.0 - 1.0
    severity = Column(Float, nullable=True)                     # 0.0 - 3.0
    condition_context = Column(String(50), nullable=True)       # stress / anxiety / depression (from user's current state)

    # CBT reframe suggestion (generated based on distortion + user context)
    reframe_suggestion = Column(Text, nullable=True)
    cbt_explanation = Column(Text, nullable=True)

    # User feedback on the analysis
    user_found_helpful = Column(Boolean, nullable=True)         # Did the user find the reframe helpful?

    created_at = Column(DateTime, default=datetime.now)
