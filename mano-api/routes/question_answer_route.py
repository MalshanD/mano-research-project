from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from db.database import get_db
from lib.assesment import question_answer as qa_lib
from schemas.assesment import questionAnswerInSchema as QAIS
from schemas.assesment import questionAnswerOutSchema as QAOS
from schemas.assesment import responseOutSchema as ROS


router = APIRouter(
    prefix="/answers",
    tags=["assesment"],
)


@router.post("/submit")
async def submit_assessment(
    data: QAIS.QuestionAnswerInSchema,
    db: Session = Depends(get_db)
):
    return await qa_lib.submit_answers(db, data)


# @router.get(
#     "/user/{user_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=list[QAOS.QuestionAnswerOutSchema],
# )
# def get_answers_by_user(user_id: int, db: Session = Depends(get_db)):
#     """Get all answers submitted by a specific user."""
#     return qa_lib.get_answers_by_user(db, user_id)


# @router.get(
#     "/question/{question_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=list[QAOS.QuestionAnswerOutSchema],
# )
# def get_answers_by_question(question_id: int, db: Session = Depends(get_db)):
#     """Get all answers for a specific question."""
#     return qa_lib.get_answers_by_question(db, question_id)
