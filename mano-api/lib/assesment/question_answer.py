from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from model.question_answers import QuestionAnswer
from model.users import User
from model.response import Response
from model.question import Question   # Import Question model
from lib.assesment.predictor import predict

# Dynamically build question_id → feature_name mapping from the database
def get_feature_map(db: Session):
    questions = db.query(Question).all()
    return {q.id: q.question_name for q in questions}


async def submit_answers(db: Session, data):

    # 1️⃣ Validate user
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 2️⃣ Get question_type_id from first question
    if not data.answers:
        raise HTTPException(
            status_code=400,
            detail="No answers provided"
        )

    first_question_id = data.answers[0].question_id

    question = db.query(Question).filter(
        Question.id == first_question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    question_type_id = question.question_type_id

    # 3️⃣ Build feature map dynamically from DB
    feature_map = get_feature_map(db)

    # 4️⃣ Remove old answers
    db.query(QuestionAnswer).filter(
        QuestionAnswer.user_id == data.user_id
    ).delete()

    # 5️⃣ Save answers
    input_dict = {}

    for item in data.answers:

        # Optional safety check: ensure all questions belong to same type
        q = db.query(Question).filter(Question.id == item.question_id).first()
        if q.question_type_id != question_type_id:
            raise HTTPException(
                status_code=400,
                detail="All questions must belong to same question type"
            )

        db_answer = QuestionAnswer(
            user_id=data.user_id,
            question_id=item.question_id,
            answer=item.answer
        )
        db.add(db_answer)

        # Build ML input using dynamic feature map
        feature = feature_map.get(item.question_id)
        if feature:
            input_dict[feature] = item.answer

    db.commit()

    # 5️⃣ Validate all 16 features present
    if len(input_dict) != 16:
        raise HTTPException(
            status_code=400,
            detail="All 16 questions must be answered"
        )

    # 6️⃣ Run prediction
    prediction = predict(input_dict)

    # 7️⃣ Save prediction to response table
    db_response = Response(
        user_id=data.user_id,
        question_type_id=question_type_id,   # ✅ now correctly assigned
        stress_score=prediction["stress"]["score"],
        stress_level=prediction["stress"]["risk_level"],
        anxiety_score=prediction["anxiety"]["score"],
        anxiety_level=prediction["anxiety"]["risk_level"],
        depression_score=prediction["depression"]["score"],
        depression_level=prediction["depression"]["risk_level"],
    )

    db.add(db_response)
    db.commit()
    db.refresh(db_response)

    return {
        "message": "Answers saved & prediction completed",
        "results": prediction
    }
