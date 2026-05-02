"""Response model — stores computed mental health scores from assessment answers.

Each row = one completed assessment. The Keras Dense NN (Component 2) produces
scores 0–100 for stress/anxiety/depression, which are classified into levels
(Low/Moderate/High) and stored here for historical tracking and trajectory analysis.
"""
from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from db.base import Base
from datetime import datetime


class Response(Base):
    """Persisted output of the risk prediction model for one user assessment."""
    __tablename__ = "response"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))              # Who took the assessment
    question_type_id = Column(Integer, ForeignKey("question_type.id"), nullable=True)

    # Stress head output (0–100 score + Low/Moderate/High label)
    stress_score = Column(Float)
    stress_level = Column(String(50))

    # Anxiety head output
    anxiety_score = Column(Float)
    anxiety_level = Column(String(50))

    # Depression head output
    depression_score = Column(Float)
    depression_level = Column(String(50))

    created_at = Column(DateTime, default=datetime.now)
