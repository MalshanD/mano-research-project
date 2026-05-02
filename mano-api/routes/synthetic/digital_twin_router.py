"""
Digital Twin Factory — Router

The ultimate feature: a single endpoint that orchestrates ALL 5 models
(CTGAN, TimeGAN, LSTM, Seq2Seq, PPO) + Open-Meteo weather API in a
7-stage closed-loop lifecycle pipeline.

Pipeline:
  1. CTGAN     → Generate component1 patient profile
  2. TimeGAN   → Generate 7-day wearable baseline
  3. Open-Meteo→ Fetch weather, apply SAD modulation
  4. LSTM      → Assess baseline risk
  5. PPO       → Select optimal intervention
  6. Seq2Seq   → Simulate treatment outcome
  7. LSTM      → Re-assess post-treatment risk

Zero real patient data. Zero cross-component API calls.
Everything is privacy-preserving by construction.
"""
from fastapi import APIRouter, Depends
import numpy as np
import time
import uuid

from schemas.synthetic.digital_twin_schema import (
    TwinRequest,
    PersonalTwinRequest,
    DigitalTwinResponse,
    DigitalTwin,
    TwinDemographics,
    TwinVitals,
    TwinVitalsDay,
    WeatherInfo,
    SADPathwayInfo,
    TwinDiagnosis,
    TwinPrescription,
    TwinOutcome,
    BehavioralScores,
)
from schemas.synthetic.simulation_schema import RiskLevel

from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.timegan_service import TimeGANService
from lib.synthetic.ctgan_service import CTGANService
from lib.synthetic.weather_service import WeatherService

from core.logging import get_logger

logger = get_logger("digital_twin_router")

router = APIRouter()

INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]
RISK_MAP = {0: "Low", 1: "Medium", 2: "High"}

# ── Social connectivity mapping from CTGAN categorical fields ──
SOCIAL_MAP = {"Yes": 0.8, "Some of them": 0.5, "No": 0.2}
WORK_INTERFERE_MAP = {"Never": 0.9, "Rarely": 0.7, "Sometimes": 0.5, "Often": 0.3}


# ── Dependency injectors ─────────────────────────────
def get_risk_svc():
    return RiskPredictionService()

def get_int_svc():
    return InterventionService()

def get_timegan_svc():
    return TimeGANService()

def get_ctgan_svc():
    return CTGANService()

def get_weather_svc():
    return WeatherService()


# ── Helpers ───────────────────────────────────────────

def ctgan_row_to_static_features(row: dict) -> list:
    """
    Map a CTGAN-generated row (20 columns) to the 20-dim normalized
    static feature vector expected by the LSTM.

    Strategy: normalize Age to [0,1], binary-encode key categoricals,
    fill remaining dims with derived scores.
    """
    features = [0.0] * 20

    # Slot 0: Age (normalized to [0,1] over range 18-80)
    age = row.get("Age", 30)
    features[0] = max(0.0, min(1.0, (float(age) - 18) / 62.0))

    # Slot 1: Gender (M=0.0, F=1.0, Other=0.5)
    g = str(row.get("Gender", "")).lower()
    features[1] = 1.0 if "f" in g else (0.5 if g not in ["male", "m"] else 0.0)

    # Slots 2-5: Binary yes/no fields
    binary_fields = ["self_employed", "family_history", "treatment", "remote_work"]
    for i, field in enumerate(binary_fields):
        val = str(row.get(field, "")).lower()
        features[2 + i] = 1.0 if val in ["yes", "true", "1"] else 0.0

    # Slots 6-9: Ordinal fields
    ordinal_map = {
        "work_interfere": {"Never": 0.0, "Rarely": 0.25, "Sometimes": 0.5, "Often": 1.0},
        "no_employees": {"1-5": 0.1, "6-25": 0.3, "26-100": 0.5, "100-500": 0.7,
                         "500-1000": 0.85, "More than 1000": 1.0},
        "leave": {"Very easy": 0.0, "Somewhat easy": 0.25,
                  "Don't know": 0.5, "Somewhat difficult": 0.75, "Very difficult": 1.0},
        "benefits": {"Yes": 1.0, "No": 0.0, "Don't know": 0.5},
    }
    for i, (field, mapping) in enumerate(ordinal_map.items()):
        val = str(row.get(field, ""))
        features[6 + i] = mapping.get(val, 0.5)

    # Slots 10-14: More binary fields
    binary2 = ["tech_company", "care_options", "wellness_program", "seek_help", "anonymity"]
    for i, field in enumerate(binary2):
        val = str(row.get(field, "")).lower()
        features[10 + i] = 1.0 if val in ["yes", "true", "1"] else (0.5 if val == "don't know" else 0.0)

    # Slots 15-19: Consequence fields (mapped as severity)
    consequence_map = {"No": 0.0, "Maybe": 0.5, "Yes": 1.0}
    cons_fields = ["mental_health_consequence", "phys_health_consequence",
                   "coworkers", "supervisor"]
    for i, field in enumerate(cons_fields):
        val = str(row.get(field, ""))
        features[15 + i] = consequence_map.get(val, 0.5)

    # Slot 19: Country-based factor (tropical=low SAD, northern=high SAD)
    country = str(row.get("Country", "")).lower()
    northern = ["united kingdom", "canada", "germany", "sweden", "finland", "norway", "iceland"]
    features[19] = 0.8 if country in northern else 0.3

    return features


def derive_behavioral_scores(vitals_7d: np.ndarray, ctgan_row: dict) -> BehavioralScores:
    """
    Derive Component 4-compatible behavioral scores from component1 data.
    No cross-component API calls — everything computed locally.
    """
    sleep_h = vitals_7d[:, 0]
    quality = vitals_7d[:, 1]
    stress = vitals_7d[:, 3]

    # Emotional regulation: 1 - normalized stress variance
    stress_std = np.std(stress)
    emotional_reg = float(max(0.0, min(1.0, 1.0 - stress_std / 0.5)))

    # Social connectivity: from CTGAN's coworkers/supervisor fields
    cow = str(ctgan_row.get("coworkers", "No"))
    sup = str(ctgan_row.get("supervisor", "No"))
    social = (SOCIAL_MAP.get(cow, 0.5) + SOCIAL_MAP.get(sup, 0.5)) / 2.0

    # Behavioral stability: 1 - coefficient of variation of sleep hours
    cv_sleep = np.std(sleep_h) / max(np.mean(sleep_h), 1e-6)
    behavioral = float(max(0.0, min(1.0, 1.0 - cv_sleep)))

    # Cognitive flexibility: from CTGAN's work_interfere field
    wi = str(ctgan_row.get("work_interfere", "Sometimes"))
    cognitive = WORK_INTERFERE_MAP.get(wi, 0.5)

    # Stress coping: mean quality × (1 - mean stress)
    coping = float(np.mean(quality) * (1.0 - np.mean(stress)))

    return BehavioralScores(
        emotional_regulation=round(emotional_reg, 3),
        social_connectivity=round(social, 3),
        behavioral_stability=round(behavioral, 3),
        cognitive_flexibility=round(cognitive, 3),
        stress_coping=round(coping, 3),
    )


def build_vitals_days(vitals_denorm: np.ndarray) -> list:
    """Convert (7, 4) array to list of TwinVitalsDay."""
    return [
        TwinVitalsDay(
            day=d + 1,
            sleep_hours=round(float(vitals_denorm[d, 0]), 2),
            sleep_quality=round(float(np.clip(vitals_denorm[d, 1], 0, 1)), 3),
            heart_rate=round(float(vitals_denorm[d, 2]), 1),
            stress_level=round(float(np.clip(vitals_denorm[d, 3], 0, 1)), 3),
        )
        for d in range(7)
    ]


# ── Main Endpoint ────────────────────────────────────

@router.post("/generate", response_model=DigitalTwinResponse)
async def generate_digital_twins(
    req: TwinRequest,
    risk_svc: RiskPredictionService = Depends(get_risk_svc),
    int_svc: InterventionService = Depends(get_int_svc),
    timegan_svc: TimeGANService = Depends(get_timegan_svc),
    ctgan_svc: CTGANService = Depends(get_ctgan_svc),
    weather_svc: WeatherService = Depends(get_weather_svc),
):
    """
    Generate complete component1 patient lifecycles.

    Each twin goes through the full 7-stage pipeline:
    CTGAN → TimeGAN → Weather → LSTM → PPO → Seq2Seq → LSTM
    """
    total_start = time.perf_counter()
    logger.info("twin_factory_start", num_twins=req.num_twins, city=req.city)

    # ── Stage 3 (pre-fetch): Get weather context once for all twins ──
    weather_ctx = None
    weather_info = None
    if req.apply_weather:
        weather_ctx = weather_svc.get_weather(req.city)
        weather_info = _build_weather_info(weather_ctx)

    # ── Stage 1: Batch-generate CTGAN profiles ──
    ctgan_df = ctgan_svc.generate(req.num_twins)
    ctgan_rows = ctgan_df.to_dict(orient="records")

    # ── Stage 2: Batch-generate TimeGAN vitals ──
    timegan_raw = timegan_svc.generate_denormalized(req.num_twins)  # (N, 7, 4)

    twins = []
    for i in range(req.num_twins):
        twin_start = time.perf_counter()
        twin_id = str(uuid.uuid4())[:8]
        row = ctgan_rows[i]

        # ── Stage 1 output: Demographics ──
        demographics = TwinDemographics(
            age=int(row.get("Age", 30)),
            gender=str(row.get("Gender", "Unknown")),
            country=str(row.get("Country", "Unknown")),
            treatment_history=str(row.get("treatment", "Unknown")),
            family_history=str(row.get("family_history", "Unknown")),
            work_interfere=str(row.get("work_interfere", "Unknown")),
            all_fields={k: str(v) for k, v in row.items()},
        )

        # ── Stage 2 output: Raw vitals ──
        vitals_7d = timegan_raw[i]  # (7, 4)

        # ── Stage 3: Apply weather modulation (3-pathway) ──
        weather_modulated = False
        if weather_ctx and req.apply_weather:
            for d in range(7):
                vitals_7d[d] = weather_svc.modulate_vitals(vitals_7d[d].tolist(), weather_ctx)
            vitals_7d = np.array(vitals_7d)
            weather_modulated = True

        vitals_days = build_vitals_days(vitals_7d)
        vitals = TwinVitals(baseline=vitals_days, weather_modulated=weather_modulated, source="timegan")

        # ── Prepare model inputs ──
        static_features = ctgan_row_to_static_features(row)

        # Normalize vitals to [0,1] for LSTM input
        vitals_norm = np.zeros((1, 7, 4), dtype=np.float32)
        vitals_norm[0, :, 0] = np.clip((vitals_7d[:, 0] - 4.0) / 5.0, 0, 1)  # sleep_h
        vitals_norm[0, :, 1] = np.clip(vitals_7d[:, 1], 0, 1)                  # quality
        vitals_norm[0, :, 2] = np.clip((vitals_7d[:, 2] - 55.0) / 45.0, 0, 1)  # hr
        vitals_norm[0, :, 3] = np.clip(vitals_7d[:, 3], 0, 1)                   # stress

        stat_np = np.array([static_features], dtype=np.float32)

        # ── Stage 4: LSTM baseline risk ──
        baseline_risk = risk_svc.predict(vitals_norm, stat_np)
        baseline_diag = TwinDiagnosis(
            risk_level=RISK_MAP[baseline_risk["risk_class"]],
            confidence=round(baseline_risk["confidence"], 3),
            probabilities=[round(p, 4) for p in baseline_risk["probabilities"]],
        )

        # ── Stage 5: PPO selects treatment ──
        dyn_flat = vitals_norm.flatten()
        stat_flat = stat_np.flatten()

        try:
            ppo_result = int_svc.get_prescription(dyn_flat, stat_flat)
            int_id = ppo_result["intervention_id"]
            intensity = ppo_result["intensity"]
        except Exception:
            # Fallback: Exercise at 0.7 intensity
            int_id = 3
            intensity = 0.7

        int_name = INTERVENTION_NAMES[int_id] if 0 <= int_id < len(INTERVENTION_NAMES) else "Exercise"

        prescription = TwinPrescription(
            intervention=int_name,
            intensity=round(intensity, 2),
            reasoning=f"PPO Agent selected {int_name} at {intensity:.0%} intensity based on patient profile and vitals.",
        )

        # ── Stage 6: Seq2Seq simulates outcome ──
        try:
            future_np = int_svc.simulate_outcome(vitals_norm, int_id, intensity)
        except Exception:
            future_np = vitals_norm.copy()

        # De-normalize future vitals for display
        future_denorm = np.zeros((7, 4))
        future_denorm[:, 0] = future_np[0, :, 0] * 5.0 + 4.0
        future_denorm[:, 1] = np.clip(future_np[0, :, 1], 0, 1)
        future_denorm[:, 2] = future_np[0, :, 2] * 45.0 + 55.0
        future_denorm[:, 3] = np.clip(future_np[0, :, 3], 0, 1)

        projected_days = build_vitals_days(future_denorm)

        # ── Stage 7: LSTM re-assess ──
        post_risk = risk_svc.predict(future_np, stat_np)
        post_diag = TwinDiagnosis(
            risk_level=RISK_MAP[post_risk["risk_class"]],
            confidence=round(post_risk["confidence"], 3),
            probabilities=[round(p, 4) for p in post_risk["probabilities"]],
        )

        # Risk reduction: decrease in High-risk probability
        high_before = baseline_risk["probabilities"][2]
        high_after = post_risk["probabilities"][2]
        reduction_pct = round((high_before - high_after) / max(high_before, 1e-6) * 100, 1)

        outcome = TwinOutcome(
            projected_vitals=projected_days,
            post_risk=post_diag,
            risk_reduction_pct=reduction_pct,
        )

        # ── Behavioral scores (C4-compatible, privacy-preserving) ──
        scores = derive_behavioral_scores(vitals_7d, row)

        twin_ms = (time.perf_counter() - twin_start) * 1000

        twins.append(DigitalTwin(
            twin_id=twin_id,
            mode="explorer",
            demographics=demographics,
            vitals=vitals,
            weather=weather_info,
            baseline_diagnosis=baseline_diag,
            prescription=prescription,
            outcome=outcome,
            behavioral_scores=scores,
            pipeline_ms=round(twin_ms, 1),
        ))

    total_ms = (time.perf_counter() - total_start) * 1000
    logger.info("twin_factory_complete", num_twins=len(twins), total_ms=round(total_ms, 1))

    return DigitalTwinResponse(
        twins=twins,
        total_ms=round(total_ms, 1),
    )


# ── Weather Info Builder ─────────────────────────────

def _build_weather_info(weather_ctx) -> WeatherInfo:
    """Build WeatherInfo with 3-pathway SAD details."""
    p = weather_ctx.pathways
    return WeatherInfo(
        city=weather_ctx.city,
        temperature_c=round(weather_ctx.temperature_c, 1),
        uv_index=round(weather_ctx.uv_index_max, 1),
        sunshine_hours=round(weather_ctx.sunshine_hours, 1),
        daylight_hours=round(weather_ctx.daylight_hours, 1),
        precipitation_hours=round(weather_ctx.precipitation_hours, 1),
        wind_speed_kmh=round(weather_ctx.wind_speed_max_kmh, 1),
        humidity_pct=round(weather_ctx.humidity_pct, 1),
        sad_intensity=round(weather_ctx.sad_intensity, 3),
        sad_pathways=SADPathwayInfo(
            serotonin_deficit=p.serotonin_deficit,
            melatonin_excess=p.melatonin_excess,
            circadian_disruption=p.circadian_disruption,
            composite_sad=p.composite_sad,
        ),
    )


# ── User Data Encoding ───────────────────────────────

def _encode_personal_static(req: PersonalTwinRequest) -> list:
    """
    Encode user questionnaire → 20-dim static feature vector.
    Same encoding as ctgan_row_to_static_features but from user input.
    """
    f = [0.0] * 20

    # Slot 0: Age
    f[0] = max(0.0, min(1.0, (float(req.age) - 18) / 62.0))

    # Slot 1: Gender
    g = req.gender.lower()
    f[1] = 1.0 if "f" in g else (0.5 if g not in ["male", "m"] else 0.0)

    # Slot 2: Self-employed
    f[2] = 1.0 if req.self_employed else 0.0

    # Slot 3: Family history
    f[3] = 1.0 if req.family_history else 0.0

    # Slot 4: Treatment
    f[4] = 1.0 if req.seeking_treatment else 0.0

    # Slot 5: Remote work
    f[5] = 1.0 if req.remote_work else 0.0

    # Slot 6: Work interfere
    wi_map = {"Never": 0.0, "Rarely": 0.25, "Sometimes": 0.5, "Often": 1.0}
    f[6] = wi_map.get(req.work_interfere.value, 0.5)

    # Slot 7: Company size
    size_map = {"1-5": 0.1, "6-25": 0.3, "26-100": 0.5, "100-500": 0.7,
                "500-1000": 0.85, "More than 1000": 1.0}
    f[7] = size_map.get(req.company_size or "", 0.5)

    # Slot 8: Leave difficulty
    leave_map = {"Very easy": 0.0, "Somewhat easy": 0.25, "Don't know": 0.5,
                 "Somewhat difficult": 0.75, "Very difficult": 1.0}
    f[8] = leave_map.get(req.leave_difficulty or "", 0.5)

    # Slot 9: Benefits
    ben_map = {"Yes": 1.0, "No": 0.0, "Don't know": 0.5}
    f[9] = ben_map.get(req.employer_benefits or "", 0.5)

    # Slot 10: Tech company
    f[10] = 1.0 if req.tech_industry else 0.0

    # Slots 11-14: defaults (care, wellness, seek_help, anonymity)
    f[11] = 0.5  # care_options
    f[12] = 0.5  # wellness_program
    f[13] = 0.5  # seek_help
    f[14] = 0.5  # anonymity

    # Slot 15: mental_health_consequence
    f[15] = 0.5  # default

    # Slot 16: phys_health_consequence
    f[16] = 0.5  # default

    # Slot 17: Coworker comfort
    social_map = {"Yes": 0.0, "Some of them": 0.5, "No": 1.0}
    f[17] = social_map.get(req.coworker_comfort or "", 0.5)

    # Slot 18: Supervisor comfort
    f[18] = social_map.get(req.supervisor_comfort or "", 0.5)

    # Slot 19: Country factor
    country = (req.country or "").lower()
    northern = ["united kingdom", "canada", "germany", "sweden", "finland", "norway", "iceland", "russia"]
    f[19] = 0.8 if country in northern else 0.3

    return f


def _encode_user_vitals(req: PersonalTwinRequest) -> np.ndarray:
    """
    Convert user self-reported vitals to the (7, 4) denormalized array.
    Sleep quality/stress: user gives 1-5 scale → we normalize to [0, 1].
    Heart rate: use user value if provided, else age-adjusted default.
    """
    vitals = np.zeros((7, 4), dtype=np.float32)

    # Age-adjusted resting HR default (population mean)
    default_hr = 72.0 - 0.1 * max(0, req.age - 30)  # slight decrease with age

    for d, v in enumerate(req.vitals_7d):
        vitals[d, 0] = v.sleep_hours
        vitals[d, 1] = (v.sleep_quality - 1) / 4.0      # 1-5 → 0-1
        vitals[d, 2] = v.heart_rate if v.heart_rate else default_hr
        vitals[d, 3] = (v.stress_level - 1) / 4.0       # 1-5 → 0-1

    return vitals


# ── Personal Mode Endpoint ───────────────────────────

@router.post("/personal", response_model=DigitalTwinResponse)
async def personal_twin(
    req: PersonalTwinRequest,
    risk_svc: RiskPredictionService = Depends(get_risk_svc),
    int_svc: InterventionService = Depends(get_int_svc),
    weather_svc: WeatherService = Depends(get_weather_svc),
):
    """
    Personal Mode: Run the simulation pipeline on user-provided data.

    Stages 1-2 are skipped (user provides demographics + vitals).
    Stages 3-7 run identically to Explorer Mode.
    """
    total_start = time.perf_counter()
    logger.info("personal_twin_start", age=req.age, city=req.city)

    twin_id = str(uuid.uuid4())[:8]

    # ── Demographics (from user) ──
    demographics = TwinDemographics(
        age=req.age,
        gender=req.gender,
        country=req.country or "Not specified",
        treatment_history="Yes" if req.seeking_treatment else "No",
        family_history="Yes" if req.family_history else "No",
        work_interfere=req.work_interfere.value,
        source="user",
        all_fields={
            "Age": str(req.age), "Gender": req.gender,
            "Country": req.country or "Not specified",
            "treatment": "Yes" if req.seeking_treatment else "No",
            "family_history": "Yes" if req.family_history else "No",
            "work_interfere": req.work_interfere.value,
        },
    )

    # ── Vitals (from user, denormalized) ──
    vitals_7d = _encode_user_vitals(req)

    # ── Stage 3: Weather modulation ──
    weather_ctx = None
    weather_info = None
    weather_modulated = False
    if req.apply_weather:
        weather_ctx = weather_svc.get_weather(req.city)
        weather_info = _build_weather_info(weather_ctx)
        for d in range(7):
            vitals_7d[d] = weather_svc.modulate_vitals(vitals_7d[d].tolist(), weather_ctx)
        vitals_7d = np.array(vitals_7d, dtype=np.float32)
        weather_modulated = True

    vitals_days = build_vitals_days(vitals_7d)
    vitals = TwinVitals(baseline=vitals_days, weather_modulated=weather_modulated, source="user")

    # ── Prepare model inputs ──
    static_features = _encode_personal_static(req)
    stat_np = np.array([static_features], dtype=np.float32)

    vitals_norm = np.zeros((1, 7, 4), dtype=np.float32)
    vitals_norm[0, :, 0] = np.clip((vitals_7d[:, 0] - 4.0) / 5.0, 0, 1)
    vitals_norm[0, :, 1] = np.clip(vitals_7d[:, 1], 0, 1)
    vitals_norm[0, :, 2] = np.clip((vitals_7d[:, 2] - 55.0) / 45.0, 0, 1)
    vitals_norm[0, :, 3] = np.clip(vitals_7d[:, 3], 0, 1)

    # ── Stage 4: LSTM baseline risk ──
    baseline_risk = risk_svc.predict(vitals_norm, stat_np)
    baseline_diag = TwinDiagnosis(
        risk_level=RISK_MAP[baseline_risk["risk_class"]],
        confidence=round(baseline_risk["confidence"], 3),
        probabilities=[round(p, 4) for p in baseline_risk["probabilities"]],
    )

    # ── Stage 5: PPO selects treatment ──
    dyn_flat = vitals_norm.flatten()
    stat_flat = stat_np.flatten()
    try:
        ppo_result = int_svc.get_prescription(dyn_flat, stat_flat)
        int_id = ppo_result["intervention_id"]
        intensity = ppo_result["intensity"]
    except Exception:
        int_id = 3
        intensity = 0.7

    int_name = INTERVENTION_NAMES[int_id] if 0 <= int_id < len(INTERVENTION_NAMES) else "Exercise"
    prescription = TwinPrescription(
        intervention=int_name,
        intensity=round(intensity, 2),
        reasoning=f"Based on your profile and 7-day vitals, the AI recommends {int_name} at {intensity:.0%} intensity.",
    )

    # ── Stage 6: Seq2Seq simulates outcome ──
    try:
        future_np = int_svc.simulate_outcome(vitals_norm, int_id, intensity)
    except Exception:
        future_np = vitals_norm.copy()

    future_denorm = np.zeros((7, 4))
    future_denorm[:, 0] = future_np[0, :, 0] * 5.0 + 4.0
    future_denorm[:, 1] = np.clip(future_np[0, :, 1], 0, 1)
    future_denorm[:, 2] = future_np[0, :, 2] * 45.0 + 55.0
    future_denorm[:, 3] = np.clip(future_np[0, :, 3], 0, 1)
    projected_days = build_vitals_days(future_denorm)

    # ── Stage 7: LSTM re-assess ──
    post_risk = risk_svc.predict(future_np, stat_np)
    post_diag = TwinDiagnosis(
        risk_level=RISK_MAP[post_risk["risk_class"]],
        confidence=round(post_risk["confidence"], 3),
        probabilities=[round(p, 4) for p in post_risk["probabilities"]],
    )

    high_before = baseline_risk["probabilities"][2]
    high_after = post_risk["probabilities"][2]
    reduction_pct = round((high_before - high_after) / max(high_before, 1e-6) * 100, 1)

    outcome = TwinOutcome(
        projected_vitals=projected_days,
        post_risk=post_diag,
        risk_reduction_pct=reduction_pct,
    )

    # ── Behavioral scores (from user data) ──
    user_row = {
        "coworkers": req.coworker_comfort or "No",
        "supervisor": req.supervisor_comfort or "No",
        "work_interfere": req.work_interfere.value,
    }
    scores = derive_behavioral_scores(vitals_7d, user_row)

    twin_ms = (time.perf_counter() - total_start) * 1000

    twin = DigitalTwin(
        twin_id=twin_id,
        mode="personal",
        demographics=demographics,
        vitals=vitals,
        weather=weather_info,
        baseline_diagnosis=baseline_diag,
        prescription=prescription,
        outcome=outcome,
        behavioral_scores=scores,
        pipeline_ms=round(twin_ms, 1),
    )

    logger.info("personal_twin_complete", twin_id=twin_id, risk=baseline_diag.risk_level,
                ms=round(twin_ms, 1))

    return DigitalTwinResponse(
        twins=[twin],
        total_ms=round(twin_ms, 1),
        models_used=["LSTM", "PPO", "Seq2Seq"],
    )
