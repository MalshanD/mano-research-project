from fastapi import APIRouter, Depends, status
from db.database import get_db
from sqlalchemy.orm import Session
from lib.assesment import question
from schemas.assesment import questionInSchema as QIS
from schemas.assesment import questionOutSchema as QOS
from schemas.assesment import assesmentTypeOutSchema as ATOS


router = APIRouter(
    prefix="/question",
    tags=["assesment"]
)


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model=ATOS.SuccessMessage
)
async def create_question(data: QIS.QuestionInSchema, db: Session = Depends(get_db)):
    """Create a single question."""
    return await question.create_question(db, data)


@router.post(
    "/create-bulk/",
    status_code=status.HTTP_201_CREATED,
    response_model=ATOS.SuccessMessage
)
async def create_bulk_questions(data: QIS.QuestionBulkInSchema, db: Session = Depends(get_db)):
    """Create multiple questions at once with a shared question_type_id."""
    return await question.create_bulk_questions(db, data)


@router.get(
    "/all/",
    status_code=status.HTTP_200_OK,
    response_model=list[QOS.QuestionOutSchema]
)
def get_all_question(db: Session = Depends(get_db)):
    return question.get_all_question(db)


@router.get(
    "/by-assessment/{assesment_type_id}",
    response_model=list[QOS.QuestionOut]
)
async def get_by_assesment_type_id(
    assesment_type_id: int,
    db: Session = Depends(get_db)
):
    return await question.get_by_assesment_type_id(db, assesment_type_id)


@router.put(
    "/update/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def update_question(id: int, data: QIS.QuestionUpdateSchema, db: Session = Depends(get_db)):
    return await question.update_question(db, id, data)


@router.delete(
    "/delete/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def delete_question(id: int, db: Session = Depends(get_db)):
    return await question.delete_question(db, id)
