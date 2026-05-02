from sqlalchemy.orm import Session
from model.question import Question
from model.question_choices import QuestionChoice
from schemas.assesment.questionInSchema import QuestionInSchema, QuestionUpdateSchema, QuestionBulkInSchema
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

async def create_question(db: Session, data: QuestionInSchema):
    """
    Create a question and optionally save multiple choices.
    """
    # Create the question
    db_question = Question(
        question_type_id=data.question_type_id,
        question_name=data.question_name
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    # Save choices if provided
    if data.choices:
        for choice_name in data.choices:
            db_choice = QuestionChoice(
                question_id=db_question.id,
                answer_name=choice_name
            )
            db.add(db_choice)
        db.commit()

    # 3️⃣ Return response
    return {
        "message": "Question created successfully"
    }


async def create_bulk_questions(db: Session, data: QuestionBulkInSchema):
    """
    Insert a list of questions in a single transaction.
    Each question can optionally have multiple choices.
    """

    saved_questions = []

    for q in data.questions_data:
        # Save question
        db_question = Question(
            question_type_id=data.question_type_id,
            question_name=q.question_name
        )
        db.add(db_question)
        db.flush()  # Flush to get db_question.id before committing

        # Save question choices if provided
        if q.choices:  # Optional list of choices
            db_choices = [
                QuestionChoice(question_id=db_question.id, answer_name=choice)
                for choice in q.choices
            ]
            db.add_all(db_choices)

        saved_questions.append(db_question)

    # Commit all at once
    db.commit()
    for q in saved_questions:
        db.refresh(q)

    return {"message": f"{len(saved_questions)} question(s) created successfully"}


def get_all_question(db: Session):
    questions = db.query(Question).options(joinedload(Question.choices)).all()
    return [
        {
            "id": q.id,
            "question_type_id": q.question_type_id,
            "question_name": q.question_name,
            "choices": [
                {"id": c.id, "answer_name": c.answer_name}
                for c in q.choices
            ] if q.choices else None
        }
        for q in questions
    ]


async def get_by_assesment_type_id(db: Session, assesment_type_id: int):
    return db.query(Question).filter(
        Question.question_type_id == assesment_type_id
    ).all()


async def update_question(db: Session, id: int, data: QuestionUpdateSchema):

    db_question = db.query(Question).filter(Question.id == id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    update_data = data.model_dump(exclude_unset=True)

    # Update question fields (exclude choices)
    if "question_name" in update_data:
        db_question.question_name = update_data["question_name"]
    if "question_type_id" in update_data:
        db_question.question_type_id = update_data["question_type_id"]

    # Replace choices if provided
    if "choices" in update_data and update_data["choices"] is not None:
        db.query(QuestionChoice).filter(QuestionChoice.question_id == id).delete()
        for choice_name in update_data["choices"]:
            db.add(QuestionChoice(question_id=id, answer_name=choice_name))

    db.commit()
    db.refresh(db_question)
    return {"message": "Question updated successfully"}


async def delete_question(db: Session, id: int):

    db_question = db.query(Question).filter(Question.id == id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Delete associated choices first
    db.query(QuestionChoice).filter(QuestionChoice.question_id == id).delete()
    db.delete(db_question)
    db.commit()
    return {"message": "Question deleted successfully"}
