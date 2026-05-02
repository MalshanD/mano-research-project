from sqlalchemy import Column, Integer, String, DateTime
from db.base import Base
from datetime import datetime

class QuestionType(Base):
    __tablename__ = "question_type"

    id = Column(Integer, primary_key=True, index=True)
    question_types = Column(String(255))
    assesment_duration = Column(String(255))
    create_date = Column(DateTime, default=datetime.now)
    description = Column(String(500))
