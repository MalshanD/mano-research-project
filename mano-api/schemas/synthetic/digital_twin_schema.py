"""
Digital Twin Factory — Pydantic Schemas

Defines the request/response models for the 7-stage lifecycle pipeline
that orchestrates CTGAN, TimeGAN, LSTM, PPO, and Seq2Seq.

Supports two modes:
  - Explorer Mode: Fully component1 (CTGAN + TimeGAN)
  - Personal Mode: User-provided questionnaire + self-reported vitals
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


# ── EXPLORER MODE REQUEST ────────────────────────────

class TwinRequest(BaseModel):
    """Generate one or more component1 digital twins (Explorer Mode)."""
    city: str = Field(
        "colombo",
        description="City for environmental context (weather / SAD modulation)",
    )
    num_twins: int = Field(1, ge=1, le=50, description="Number of twins to generate")
    apply_weather: bool = Field(True, description="Apply SAD modulation from real weather")


# ── PERSONAL MODE INPUT ──────────────────────────────

class UserVitalsDay(BaseModel):
    """One day of self-reported vitals from the user."""
    sleep_hours: float = Field(..., ge=0, le=16, description="Hours slept last night")
    sleep_quality: int = Field(..., ge=1, le=5, description="Sleep quality (1=terrible, 5=excellent)")
    stress_level: int = Field(..., ge=1, le=5, description="Stress level (1=none, 5=extreme)")
    heart_rate: Optional[float] = Field(None, ge=40, le=200, description="Resting HR (optional, from wearable)")


class WorkInterference(str, Enum):
    NEVER = "Never"
    RARELY = "Rarely"
    SOMETIMES = "Sometimes"
    OFTEN = "Often"


class PersonalTwinRequest(BaseModel):
    """
    Personal Mode: User provides their own data for personalized simulation.

    Minimum required: age, gender, family_history, seeking_treatment,
    work_interfere, and 7 days of vitals.

    Optional fields use population-median defaults when not provided.
    """
    # ── Required Demographics (5 core fields) ──
    age: int = Field(..., ge=14, le=90, description="User's age")
    gender: str = Field(..., description="Male / Female / Non-binary / Other")
    family_history: bool = Field(
        ..., description="Family history of mental illness"
    )
    seeking_treatment: bool = Field(
        ..., description="Currently seeking or receiving treatment"
    )
    work_interfere: WorkInterference = Field(
        ..., description="How much mental health interferes with work"
    )

    # ── Required Vitals (7 days of self-report) ──
    vitals_7d: List[UserVitalsDay] = Field(
        ..., min_length=7, max_length=7,
        description="7 days of self-reported vitals (most recent first)"
    )

    # ── Optional Demographics ──
    country: Optional[str] = Field(None, description="Country of residence")
    self_employed: Optional[bool] = Field(None, description="Self-employed?")
    remote_work: Optional[bool] = Field(None, description="Works remotely?")
    tech_industry: Optional[bool] = Field(None, description="Works in tech?")
    company_size: Optional[str] = Field(None, description="1-5 / 6-25 / 26-100 / 100-500 / 500-1000 / More than 1000")
    employer_benefits: Optional[str] = Field(None, description="Yes / No / Don't know")
    leave_difficulty: Optional[str] = Field(None, description="Very easy / Somewhat easy / Don't know / Somewhat difficult / Very difficult")
    coworker_comfort: Optional[str] = Field(None, description="Yes / Some of them / No")
    supervisor_comfort: Optional[str] = Field(None, description="Yes / Some of them / No")

    # ── Environment ──
    city: str = Field("colombo", description="City for weather/SAD context")
    apply_weather: bool = Field(True, description="Apply SAD modulation")


# ── PIPELINE STAGE OUTPUTS ───────────────────────────

class TwinDemographics(BaseModel):
    """Stage 1: Patient profile (from CTGAN or user-provided)."""
    age: int
    gender: str
    country: str
    treatment_history: str
    family_history: str
    work_interfere: str
    source: str = Field("ctgan", description="'ctgan' or 'user'")
    all_fields: Dict[str, str] = Field(
        default_factory=dict,
        description="All profile fields",
    )


class TwinVitalsDay(BaseModel):
    """Single day of wearable vitals."""
    day: int
    sleep_hours: float
    sleep_quality: float
    heart_rate: float
    stress_level: float


class TwinVitals(BaseModel):
    """Stage 2+3: Vitals (generated or user-reported) + weather-modulated."""
    baseline: List[TwinVitalsDay] = Field(..., min_length=7, max_length=7)
    weather_modulated: bool = False
    source: str = Field("timegan", description="'timegan' or 'user'")


class SADPathwayInfo(BaseModel):
    """Detailed 3-pathway SAD biological scores."""
    serotonin_deficit: float = Field(..., ge=0, le=1, description="Low UV/sunshine → ↓mood, ↑stress")
    melatonin_excess: float = Field(..., ge=0, le=1, description="Short daylight → ↑sleep, fatigue")
    circadian_disruption: float = Field(..., ge=0, le=1, description="Daylight deviation → fragmented rhythm")
    composite_sad: float = Field(..., ge=0, le=1, description="Weighted overall SAD intensity")


class WeatherInfo(BaseModel):
    """Stage 3: Environmental context with SAD pathways."""
    city: str
    temperature_c: float
    uv_index: float
    sunshine_hours: float
    daylight_hours: float
    precipitation_hours: float = 0.0
    wind_speed_kmh: float = 0.0
    humidity_pct: float = 70.0
    sad_intensity: float = Field(
        ..., ge=0, le=1,
        description="Composite SAD intensity (legacy)"
    )
    sad_pathways: Optional[SADPathwayInfo] = None


class TwinDiagnosis(BaseModel):
    """Stage 4: LSTM risk assessment."""
    risk_level: str
    confidence: float
    probabilities: List[float] = Field(..., min_length=3, max_length=3)


class TwinPrescription(BaseModel):
    """Stage 5: PPO-recommended intervention."""
    intervention: str
    intensity: float
    reasoning: str


class TwinOutcome(BaseModel):
    """Stage 6+7: Seq2Seq simulation + LSTM re-assessment."""
    projected_vitals: List[TwinVitalsDay] = Field(..., min_length=7, max_length=7)
    post_risk: TwinDiagnosis
    risk_reduction_pct: float = Field(
        ..., description="Percentage reduction in risk (negative = worsened)"
    )


class BehavioralScores(BaseModel):
    """Privacy-preserving behavioral scores derived from data.
    Compatible with Component 4's GMM clustering schema."""
    emotional_regulation: float = Field(..., ge=0, le=1)
    social_connectivity: float = Field(..., ge=0, le=1)
    behavioral_stability: float = Field(..., ge=0, le=1)
    cognitive_flexibility: float = Field(..., ge=0, le=1)
    stress_coping: float = Field(..., ge=0, le=1)


# ── COMPLETE TWIN ────────────────────────────────────

class DigitalTwin(BaseModel):
    """A complete patient lifecycle (component1 or personalized)."""
    twin_id: str
    mode: str = Field("explorer", description="'explorer' or 'personal'")
    demographics: TwinDemographics
    vitals: TwinVitals
    weather: Optional[WeatherInfo] = None
    baseline_diagnosis: TwinDiagnosis
    prescription: TwinPrescription
    outcome: TwinOutcome
    behavioral_scores: BehavioralScores
    pipeline_ms: float = Field(
        ..., description="Total pipeline execution time in milliseconds"
    )


# ── RESPONSE ─────────────────────────────────────────

class DigitalTwinResponse(BaseModel):
    """API response containing one or more generated twins."""
    twins: List[DigitalTwin]
    total_ms: float
    weather_source: str = "open-meteo"
    models_used: List[str] = [
        "CTGAN", "TimeGAN", "LSTM", "PPO", "Seq2Seq"
    ]
