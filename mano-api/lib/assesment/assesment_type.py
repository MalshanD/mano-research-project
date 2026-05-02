from sqlalchemy.orm import Session
from fastapi import HTTPException
from schemas.assesment import assesmentTypeInSchema as ATIS
from model.question_type import QuestionType

async def create_assesment_type(db: Session, data: ATIS.AssesmentTypeIn):
    db_user = QuestionType(
        question_types=data.question_types,
        assesment_duration=data.assesment_duration,
        description=data.description
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "assesment type created successfully"}


def get_all_assesment_types(db: Session):
    return db.query(QuestionType).all()


async def update_assesment_type(db: Session, id: int, data: ATIS.AssesmentTypeUpdate):
    db_type = db.query(QuestionType).filter(QuestionType.id == id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Assessment type not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_type, key, value)

    db.commit()
    db.refresh(db_type)
    return {"message": "Assessment type updated successfully"}


async def delete_assesment_type(db: Session, id: int):
    db_type = db.query(QuestionType).filter(QuestionType.id == id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Assessment type not found")

    db.delete(db_type)
    db.commit()
    return {"message": "Assessment type deleted successfully"}
