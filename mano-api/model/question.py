from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base

class Question(Base):
    __tablename__ = "question"

    id = Column(Integer, primary_key=True, index=True)
    question_type_id = Column(Integer, ForeignKey("question_type.id"))
    question_name = Column(Text)

    question_type = relationship("QuestionType")
    choices = relationship("QuestionChoice", back_populates="question")
