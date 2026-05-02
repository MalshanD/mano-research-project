from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AssesmentTypeOut(BaseModel):
    id: int
    question_types: str
    assesment_duration: str
    create_date: datetime
    description: Optional[str]


class SuccessMessage(BaseModel):
    message: str
