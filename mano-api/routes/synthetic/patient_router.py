"""
Patient CRUD Router.
Manages patient profiles — create, read, update, delete.
All simulation results are linked to patients via foreign key.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from core.database import get_db
from db.database import get_db as sync_get_db
from core.logging import get_logger
from model.models import Patient, SimulationResult
from model.users import User
from model.question_answers import QuestionAnswer
from model.response import Response as UserResponse
from schemas.synthetic.patient_schema import (
    PatientCreate,
    PatientCreateFromUser,
    PatientUpdate,
    PatientResponse,
    PatientWithHistory,
    PatientListResponse,
    SimulationHistoryItem,
)

logger = get_logger("patient_router")
router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new patient in the system.
    Accepts human-readable demographic fields and initial vitals, then
    builds the internal 20-dim feature vector and 7-day history automatically.
    """
    # --- Build 20-dim static feature vector from simple fields ---
    # [0]  age normalised (0-120 → 0-1)
    # [1]  gender=M flag
    # [2]  gender=F flag
    # [3]  diagnosis present flag
    # [4]  latest_sleep_hours normalised (0-24 → 0-1)
    # [5]  latest_heart_rate normalised (40-200 → 0-1)
    # [6]  latest_stress_level (already 0-1)
    # [7–19] reserved / zero-padded for future features
    age = data.age or 0
    gender = (data.gender or '').upper()
    sleep = data.latest_sleep_hours or 7.0
    hr = data.latest_heart_rate or 72.0
    stress = data.latest_stress_level or 0.3

    static_features: list[float] = [
        age / 120.0,                          # [0]
        1.0 if gender == 'M' else 0.0,        # [1]
        1.0 if gender == 'F' else 0.0,        # [2]
        1.0 if data.diagnosis else 0.0,       # [3]
        sleep / 24.0,                         # [4]
        (hr - 40.0) / 160.0,                  # [5]
        stress,                               # [6]
    ] + [0.0] * 13                            # [7–19] padding

    # --- Build 7-day vitals history (replicate the single reading) ---
    sleep_quality = max(0.0, min(1.0, 1.0 - stress))
    day_vitals = {
        "sleep_hours": sleep,
        "sleep_quality": sleep_quality,
        "heart_rate": hr,
        "stress_level": stress,
    }
    vitals_json = [day_vitals] * 7

    patient = Patient(
        name=data.name,
        static_features=static_features,
        latest_vitals=vitals_json,
    )

    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    logger.info("patient_created", patient_id=patient.id, name=patient.name)

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        static_features=patient.static_features,
        latest_vitals=_parse_vitals(patient.latest_vitals),
        current_risk_level=patient.current_risk_level,
        risk_confidence=patient.risk_confidence,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.get("/", response_model=PatientListResponse)
async def list_patients(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    List all patients with pagination.
    """
    # Count total
    count_result = await db.execute(select(func.count(Patient.id)))
    total = count_result.scalar()

    # Fetch page
    result = await db.execute(
        select(Patient).offset(skip).limit(limit).order_by(Patient.created_at.desc())
    )
    patients = result.scalars().all()

    return PatientListResponse(
        total=total,
        patients=[
            PatientResponse(
                id=p.id,
                name=p.name,
                static_features=p.static_features,
                latest_vitals=_parse_vitals(p.latest_vitals),
                current_risk_level=p.current_risk_level,
                risk_confidence=p.risk_confidence,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in patients
        ],
    )


@router.get("/by-user/{user_id}", response_model=PatientResponse)
async def get_patient_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    sync_db: Session = Depends(sync_get_db),
):
    """
    Check whether a Patient profile already exists for the given app user_id.
    Returns the patient if found, 404 if not yet created.
    """
    # Patient name is set to the user's guest_name at creation time — look up by name
    user = sync_db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Patient)
        .where(Patient.name == user.guest_name)
        .order_by(Patient.created_at.desc())
        .limit(1)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="No patient profile for this user")

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        static_features=patient.static_features,
        latest_vitals=_parse_vitals(patient.latest_vitals),
        current_risk_level=patient.current_risk_level,
        risk_confidence=patient.risk_confidence,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.post("/from-user/{user_id}", response_model=PatientResponse, status_code=201)
async def create_patient_from_user(
    user_id: int,
    data: PatientCreateFromUser,
    db: AsyncSession = Depends(get_db),
    sync_db: Session = Depends(sync_get_db),
):
    """
    Create a Patient profile auto-populated from the logged-in user's stored data.

    Field sources:
      name             ← users.guest_name
      age              ← question_answers(question_id=1)
      gender           ← question_answers(question_id=2)  Male/Female → M/F
      sleep_hours      ← question_answers(question_id=5)
      stress_level     ← response.stress_score / 100
      diagnosis        ← highest of stress/anxiety/depression score → label
      heart_rate       ← request body (only field asked from user)
    """
    # 1. Validate user + get name
    user = sync_db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    name = user.guest_name or f"User {user_id}"

    # 2. Age from question_answers(question_id=1)
    age_ans = sync_db.query(QuestionAnswer).filter(
        QuestionAnswer.user_id == user_id,
        QuestionAnswer.question_id == 1,
    ).first()
    try:
        age = int(age_ans.answer) if age_ans and age_ans.answer else 25
    except (ValueError, TypeError):
        age = 25

    # 3. Gender from question_answers(question_id=2)
    gender_ans = sync_db.query(QuestionAnswer).filter(
        QuestionAnswer.user_id == user_id,
        QuestionAnswer.question_id == 2,
    ).first()
    raw_gender = (gender_ans.answer or "").strip().lower() if gender_ans else ""
    gender = "M" if raw_gender in ("male", "m") else "F" if raw_gender in ("female", "f") else "M"

    # 4. Sleep hours from question_answers(question_id=5)
    sleep_ans = sync_db.query(QuestionAnswer).filter(
        QuestionAnswer.user_id == user_id,
        QuestionAnswer.question_id == 5,
    ).first()
    try:
        sleep = float(sleep_ans.answer) if sleep_ans and sleep_ans.answer else 7.0
    except (ValueError, TypeError):
        sleep = 7.0

    # 5. Latest response → stress_level + diagnosis
    latest_response = sync_db.query(UserResponse).filter(
        UserResponse.user_id == user_id,
    ).order_by(UserResponse.id.desc()).first()

    if latest_response:
        stress_level = round((latest_response.stress_score or 0) / 100.0, 4)
        scores = {
            "Anxiety Disorder":  latest_response.anxiety_score or 0,
            "Depression":        latest_response.depression_score or 0,
            "Stress Disorder":   latest_response.stress_score or 0,
        }
        diagnosis = max(scores, key=scores.get) if max(scores.values()) > 0 else None
    else:
        stress_level = 0.3
        diagnosis = None

    # 6. Build PatientCreate and reuse existing feature-vector logic
    patient_data = PatientCreate(
        name=name,
        age=age,
        gender=gender,
        diagnosis=diagnosis,
        latest_sleep_hours=sleep,
        latest_heart_rate=data.latest_heart_rate,
        latest_stress_level=stress_level,
    )

    logger.info(
        "patient_from_user",
        user_id=user_id,
        name=name,
        age=age,
        gender=gender,
        diagnosis=diagnosis,
        sleep=sleep,
        stress_level=stress_level,
        heart_rate=data.latest_heart_rate,
    )

    return await create_patient(patient_data, db)


@router.get("/{patient_id}", response_model=PatientWithHistory)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a single patient with their full simulation history.
    """
    result = await db.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .options(selectinload(Patient.simulations))
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    return PatientWithHistory(
        id=patient.id,
        name=patient.name,
        static_features=patient.static_features,
        latest_vitals=_parse_vitals(patient.latest_vitals),
        current_risk_level=patient.current_risk_level,
        risk_confidence=patient.risk_confidence,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        simulations=[
            SimulationHistoryItem(
                id=s.id,
                intervention_type=s.intervention_type,
                intensity=s.intensity,
                original_risk=s.original_risk,
                projected_risk=s.projected_risk,
                risk_reduction_score=s.risk_reduction_score,
                created_at=s.created_at,
            )
            for s in sorted(patient.simulations, key=lambda s: s.created_at, reverse=True)
        ],
    )


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a patient's demographics or vitals.
    Only the fields you provide will be updated.
    """
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    if data.name is not None:
        patient.name = data.name
    if data.static_features is not None:
        patient.static_features = data.static_features
    if data.latest_vitals is not None:
        patient.latest_vitals = [v.model_dump() for v in data.latest_vitals]

    await db.commit()
    await db.refresh(patient)

    logger.info("patient_updated", patient_id=patient.id)

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        static_features=patient.static_features,
        latest_vitals=_parse_vitals(patient.latest_vitals),
        current_risk_level=patient.current_risk_level,
        risk_confidence=patient.risk_confidence,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a patient and all their simulation history.
    (cascade delete is defined on the ORM model)
    """
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    await db.delete(patient)
    await db.commit()

    logger.info("patient_deleted", patient_id=patient_id)


# --- HELPERS ---

def _parse_vitals(vitals_json):
    """Convert stored JSON vitals back to DayVitals schema objects."""
    if not vitals_json:
        return None
    from schemas.synthetic.simulation_schema import DayVitals
    return [DayVitals(**v) for v in vitals_json]
