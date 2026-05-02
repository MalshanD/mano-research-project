from pydantic import BaseModel
from typing import Optional


class AssesmentTypeIn(BaseModel):
    question_types: str
    assesment_duration: str
    description: Optional[str]


class AssesmentTypeUpdate(BaseModel):
    question_types: Optional[str] = None
    assesment_duration: Optional[str] = None
    description: Optional[str] = None
