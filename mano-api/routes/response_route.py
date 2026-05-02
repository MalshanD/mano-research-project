from fastapi import APIRouter, Depends, status
from typing import List
from db.database import get_db
from sqlalchemy.orm import Session
from lib.assesment import response_service as RS
from schemas.assesment.responseOutSchema import ResponseOut, ConditionResult

router = APIRouter(
    prefix="/response",
    tags=["assesment"]
)

@router.get(
    "/response/last/{user_id}",
    response_model = ResponseOut
)
async def fetch_last_response(
    user_id: int,
    db: Session = Depends(get_db)
):
    return await RS.get_last_response(db, user_id)


@router.get(
    "/response/history/{user_id}",
    response_model=List[ResponseOut]
)
async def fetch_response_history(
    user_id: int,
    db: Session = Depends(get_db)
):
    return await RS.get_response_history(db, user_id)

