from sqlalchemy import Column, Integer, String, ForeignKey
from db.base import Base

class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("question.id"))
    answer = Column(String(255))
