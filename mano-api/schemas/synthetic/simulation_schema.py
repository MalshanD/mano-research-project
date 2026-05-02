from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

# --- ENUMS (Strict Choices) ---
class InterventionType(int, Enum):
    # Matches your config! 0=Control, 1=Wellness, etc.
    CONTROL = 0
    WELLNESS_APP = 1
    CBT = 2
    EXERCISE = 3
    MEDICATION = 4

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

# --- INPUT MODELS (What the Frontend Sends) ---

class StaticFeatures(BaseModel):
    """
    User Demographics (Must match the 20 features expected by the LSTM model)
    For simplicity in this phase, we accept the raw vector,
    but in a real app, this would be fields like 'age', 'gender', etc.
    """
    features: List[float] = Field(
        ...,
        min_length=20,
        max_length=20,
        description="Normalized demographic vector (exactly 20 features)"
    )

class DayVitals(BaseModel):
    """
    One day of wearable data
    """
    sleep_hours: float = Field(..., ge=0, le=24)
    sleep_quality: float = Field(..., ge=0, le=1)
    heart_rate: float = Field(..., ge=40, le=200)
    stress_level: float = Field(..., ge=0, le=1)

class PatientState(BaseModel):
    """
    The full snapshot of a patient
    """
    static_data: StaticFeatures
    # We need exactly 7 days of history for the LSTM/Seq2Seq
    dynamic_history: List[DayVitals] = Field(..., min_length=7, max_length=7)

class SimulationRequest(BaseModel):
    """
    The 'What If?' Question
    """
    patient_state: PatientState
    intervention_type: InterventionType
    intensity: float = Field(..., ge=0.1, le=1.0, description="Intervention intensity (0.1 to 1.0)")

# --- OUTPUT MODELS (What we send back) ---

class RiskPredictionResponse(BaseModel):
    current_risk_class: RiskLevel
    confidence: float
    probabilities: List[float]

class SimulationResponse(BaseModel):
    """
    The 'Future' Timeline
    """
    original_risk: RiskPredictionResponse
    projected_risk: RiskPredictionResponse

    # The simulated 7-day trajectory
    future_vitals: List[DayVitals]

    # Difference analysis
    risk_reduction_score: float

class PrescriptionResponse(BaseModel):
    """
    What the AI Doctor recommends
    """
    recommended_intervention: str
    recommended_intensity: float
    confidence: float = 0.0
    current_risk: Optional[RiskPredictionResponse] = None
    reasoning: str = "Based on optimization of stress and sleep patterns."
