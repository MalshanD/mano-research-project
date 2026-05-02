from sqlalchemy import desc
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.response import Response
from model.users import User
from schemas.assesment.responseOutSchema import ResponseOut, ConditionResult  # your Pydantic schemas


from typing import List


async def get_last_response(db: Session, user_id: int) -> ResponseOut:

    # 1️⃣ Validate user
    user_exists = db.query(User.id).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 2️⃣ Fetch latest response (by ID is usually safer than timestamp)
    last_response = (
        db.query(Response)
        .filter(Response.user_id == user_id)
        .order_by(Response.id.desc())
        .first()
    )

    if not last_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No response found for this user"
        )

    # 3️⃣ Return structured schema
    return ResponseOut(
        user_id=last_response.user_id,
        question_type_id=last_response.question_type_id,
        stress=ConditionResult(
            score=last_response.stress_score,
            risk_level=last_response.stress_level
        ),
        anxiety=ConditionResult(
            score=last_response.anxiety_score,
            risk_level=last_response.anxiety_level
        ),
        depression=ConditionResult(
            score=last_response.depression_score,
            risk_level=last_response.depression_level
        ),
        created_at=last_response.created_at
    )


async def get_response_history(db: Session, user_id: int) -> List[ResponseOut]:

    # 1️⃣ Validate user
    user_exists = db.query(User.id).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 2️⃣ Fetch all responses for the user, newest first
    responses = (
        db.query(Response)
        .filter(Response.user_id == user_id)
        .order_by(Response.id.desc())
        .all()
    )

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No responses found for this user"
        )

    # 3️⃣ Map each response to the schema
    return [
        ResponseOut(
            user_id=r.user_id,
            question_type_id=r.question_type_id,
            stress=ConditionResult(
                score=r.stress_score,
                risk_level=r.stress_level
            ),
            anxiety=ConditionResult(
                score=r.anxiety_score,
                risk_level=r.anxiety_level
            ),
            depression=ConditionResult(
                score=r.depression_score,
                risk_level=r.depression_level
            ),
            created_at=r.created_at
        )
        for r in responses
    ]

