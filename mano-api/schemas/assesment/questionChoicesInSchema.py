from pydantic import BaseModel
from typing import Optional


class QuestionChoicesIn(BaseModel):
    answer_name: list[str]


class QuestionChoicesOut(BaseModel):
    answer_name: list[str]


class QuestionChoiceUpdate(BaseModel):
    answer_name: Optional[str] = None
