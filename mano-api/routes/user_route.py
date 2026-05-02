from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from db.database import get_db
from schemas.user import userInSchema as UIS
from lib.user import user_service as U

router = APIRouter(prefix="/users", tags=["Users"])

@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED
)
async def create_user_endpoint(
    data: UIS.UserIn,
    db: Session = Depends(get_db)
):
    return await U.create_user(db, data)
