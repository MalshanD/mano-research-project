from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ConditionResult(BaseModel):
    score: float
    risk_level: str


class ResponseOut(BaseModel):
    user_id: int
    question_type_id: Optional[int] = None

    stress: ConditionResult
    anxiety: ConditionResult
    depression: ConditionResult

    created_at: datetime

    class Config:
        from_attributes = True   # for SQLAlchemy (Pydantic v2)
