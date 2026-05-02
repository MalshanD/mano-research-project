"""
Patient CRUD Schemas.
Pydantic models for patient creation, updates, and API responses.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from schemas.synthetic.simulation_schema import DayVitals


# --- INPUT SCHEMAS ---

class PatientCreate(BaseModel):
    """
    Schema for creating a new patient profile.
    Accepts human-readable fields; the route builds the internal
    20-dim feature vector and 7-day vitals history automatically.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Patient display name")
    age: Optional[int] = Field(None, ge=0, le=120, description="Patient age in years")
    gender: Optional[str] = Field(None, description="Gender: 'M', 'F', or 'Other'")
    diagnosis: Optional[str] = Field(None, max_length=200, description="Primary diagnosis")
    latest_sleep_hours: Optional[float] = Field(7.0, ge=0, le=24, description="Most recent sleep duration (hours)")
    latest_heart_rate: Optional[float] = Field(72.0, ge=40, le=200, description="Most recent resting heart rate (bpm)")
    latest_stress_level: Optional[float] = Field(0.3, ge=0, le=1, description="Most recent stress level (0–1)")


class PatientUpdate(BaseModel):
    """Schema for updating a patient. All fields are optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    static_features: Optional[List[float]] = Field(None, min_length=20, max_length=20)
    latest_vitals: Optional[List[DayVitals]] = Field(None, min_length=7, max_length=7)


class PatientCreateFromUser(BaseModel):
    """
    Schema for creating a patient profile auto-populated from the logged-in user's data.
    Only heart rate is requested from the user — everything else is pulled from the DB.
    """
    latest_heart_rate: float = Field(
        default=72.0,
        ge=40,
        le=200,
        description="Resting heart rate in BPM (40–200). Default 72 if skipped.",
    )


# --- OUTPUT SCHEMAS ---

class SimulationHistoryItem(BaseModel):
    """One simulation record in the patient's history."""
    id: str
    intervention_type: str
    intensity: float
    original_risk: str
    projected_risk: str
    risk_reduction_score: float
    created_at: datetime


class PatientResponse(BaseModel):
    """Full patient profile returned by the API."""
    id: str
    name: str
    static_features: List[float]
    latest_vitals: Optional[List[DayVitals]] = None
    current_risk_level: Optional[str] = None
    risk_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientWithHistory(PatientResponse):
    """Patient profile with attached simulation history."""
    simulations: List[SimulationHistoryItem] = []

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    """Paginated list of patients."""
    total: int
    patients: List[PatientResponse]
