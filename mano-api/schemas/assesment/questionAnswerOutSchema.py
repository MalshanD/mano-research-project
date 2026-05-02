from pydantic import BaseModel


class QuestionAnswerOutSchema(BaseModel):
    id: int
    user_id: int
    question_id: int
    answer: str

    class Config:
        from_attributes = True
