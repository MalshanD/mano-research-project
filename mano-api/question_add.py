import sys
import os

# Add the root project dir to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import SessionLocal
from model.question_type import QuestionType
from model.question import Question

QUESTIONS = [
    "Age",
    "Gender",
    "Education_Level",
    "Employment_Status",
    "Sleep_Hours",
    "Physical_Activity_Hrs",
    "Social_Support_Score",
    "Family_History_Mental_Illness",
    "Chronic_Illnesses",
    "Therapy",
    "Meditation",
    "Financial_Stress",
    "Work_Stress",
    "Self_Esteem_Score",
    "Life_Satisfaction_Score",
    "Loneliness_Score",
]


def seed_database():
    db = SessionLocal()
    try:
        # ─── STEP 1: Create QuestionType ───────────────────────────────
        print("=" * 55)
        print("STEP 1: Creating QuestionType")
        print("=" * 55)

        q_type = db.query(QuestionType).filter(
            QuestionType.question_types == "main question"
        ).first()

        if not q_type:
            q_type = QuestionType(
                question_types="main question",
                assesment_duration="2.3",
                description="Main assessment questions for mental health prediction"
            )
            db.add(q_type)
            db.commit()
            db.refresh(q_type)
            print(f"  [CREATED] QuestionType: '{q_type.question_types}' (ID: {q_type.id})")
        else:
            q_type.assesment_duration = "2.3"
            db.commit()
            print(f"  [EXISTS]  QuestionType: '{q_type.question_types}' (ID: {q_type.id})")

        # ─── STEP 2: Create Questions ───────────────────────────────────
        print()
        print("=" * 55)
        print("STEP 2: Creating Questions")
        print("=" * 55)

        for q_name in QUESTIONS:
            existing_q = db.query(Question).filter(
                Question.question_name == q_name,
                Question.question_type_id == q_type.id
            ).first()

            if not existing_q:
                new_q = Question(
                    question_type_id=q_type.id,
                    question_name=q_name
                )
                db.add(new_q)
                db.flush()
                print(f"  [CREATED] Question: '{q_name}' (ID: {new_q.id})")
            else:
                print(f"  [EXISTS]  Question: '{q_name}' (ID: {existing_q.id})")

        db.commit()

        # ─── Summary ────────────────────────────────────────────────────
        print()
        print("=" * 55)
        print("Seeding completed successfully!")
        print(f"  QuestionType ID : {q_type.id}")
        print(f"  Total Questions : {len(QUESTIONS)}")
        print("=" * 55)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
