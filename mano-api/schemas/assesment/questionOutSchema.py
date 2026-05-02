from pydantic import BaseModel
from typing import List, Optional


class ChoiceOutSchema(BaseModel):
    id: int
    answer_name: str


class QuestionOutSchema(BaseModel):
    model_config = {"exclude_none": True}

    id: int
    question_name: str
    question_type_id: int
    choices: Optional[List[ChoiceOutSchema]] = None


class QuestionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    question_name: str
