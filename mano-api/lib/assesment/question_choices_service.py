from sqlalchemy.orm import Session
from fastapi import HTTPException
from schemas.assesment import questionChoicesInSchema as QCIS
from model.question_choices import QuestionChoice


async def create_question_choices(
    db: Session,
    data: QCIS.QuestionChoicesIn,
    question_id: int
):
    choices = []
    for answer in data.answer_name:
        db_choice = QuestionChoice(
            question_id=question_id,
            answer_name=answer
        )
        db.add(db_choice)
        choices.append(db_choice)
    db.commit()
    for choice in choices:
        db.refresh(choice)

    return {"message": "Question choices created successfully"}


async def get_by_question_id(db: Session, question_id: int):
    choices = db.query(QuestionChoice).filter(
        QuestionChoice.question_id == question_id
    ).all()
    answer_names = [c.answer_name for c in choices]

    return answer_names


async def update_question_choice(db: Session, id: int, data: QCIS.QuestionChoiceUpdate):
    db_choice = db.query(QuestionChoice).filter(QuestionChoice.id == id).first()
    if not db_choice:
        raise HTTPException(status_code=404, detail="Question choice not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_choice, key, value)

    db.commit()
    db.refresh(db_choice)
    return {"message": "Question choice updated successfully"}


async def delete_question_choice(db: Session, id: int):
    db_choice = db.query(QuestionChoice).filter(QuestionChoice.id == id).first()
    if not db_choice:
        raise HTTPException(status_code=404, detail="Question choice not found")

    db.delete(db_choice)
    db.commit()
    return {"message": "Question choice deleted successfully"}
