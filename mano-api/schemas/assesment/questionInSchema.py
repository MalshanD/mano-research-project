from pydantic import BaseModel
from typing import List, Optional


class QuestionInSchema(BaseModel):
    question_type_id: int
    question_name: str
    choices: Optional[List[str]] = None


class QuestionBulkInSchema(BaseModel):
    question_type_id: int
    questions: List[str]
    choices: Optional[List[str]] = None


class QuestionUpdateSchema(BaseModel):
    question_type_id: Optional[int] = None
    question_name: Optional[str] = None
    choices: Optional[List[str]] = None
