from pydantic import BaseModel
from typing import List


class AnswerItem(BaseModel):
    question_id: int
    answer: str


class QuestionAnswerInSchema(BaseModel):
    user_id: int
    answers: List[AnswerItem]
