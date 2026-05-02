from fastapi import APIRouter, Depends, status
from db.database import get_db
from sqlalchemy.orm import Session
from schemas.assesment import questionChoicesInSchema as QCIS
from lib.assesment import question_choices_service as QCS
from schemas.assesment import assesmentTypeOutSchema as ATOS


router = APIRouter(
    prefix="/question_choices",
    tags=["assesment"]
)


@router.post(
    "/create/{question_id}",
    status_code=status.HTTP_201_CREATED,
    response_model = ATOS.SuccessMessage
)
async def create_choices(
    question_id: int,
    data: QCIS.QuestionChoicesIn,
    db: Session = Depends(get_db)
):
    return await QCS.create_question_choices(db, data, question_id)


@router.get(
    "/by-question/{question_id}",
    status_code=200,
    response_model=QCIS.QuestionChoicesOut
)
async def get_choices_by_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    answer_names = await QCS.get_by_question_id(db, question_id)
    return {"answer_name": answer_names}


@router.put(
    "/update/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def update_question_choice(id: int, data: QCIS.QuestionChoiceUpdate, db: Session = Depends(get_db)):
    return await QCS.update_question_choice(db, id, data)


@router.delete(
    "/delete/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def delete_question_choice(id: int, db: Session = Depends(get_db)):
    return await QCS.delete_question_choice(db, id)
