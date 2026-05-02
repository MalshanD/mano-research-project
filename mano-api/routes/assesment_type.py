from fastapi import APIRouter, Depends, status
from db.database import get_db
from sqlalchemy.orm import Session
from lib.assesment import assesment_type as AT
from schemas.assesment import assesmentTypeInSchema as ATIS
from schemas.assesment import assesmentTypeOutSchema as ATOS

router = APIRouter(
    prefix="/assesment_type",
    tags=["assesment"]
)

@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model = ATOS.SuccessMessage
)
async def create_assesment_type(data:ATIS.AssesmentTypeIn, db: Session = Depends(get_db)):
    return await AT.create_assesment_type(db, data)


@router.get(
    "/all/",
    status_code=status.HTTP_200_OK,
    response_model=list[ATOS.AssesmentTypeOut]
)
def get_all_assesment_types(
    db: Session = Depends(get_db)
):
    return AT.get_all_assesment_types(db)


@router.put(
    "/update/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def update_assesment_type(id: int, data: ATIS.AssesmentTypeUpdate, db: Session = Depends(get_db)):
    return await AT.update_assesment_type(db, id, data)


@router.delete(
    "/delete/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ATOS.SuccessMessage
)
async def delete_assesment_type(id: int, db: Session = Depends(get_db)):
    return await AT.delete_assesment_type(db, id)
