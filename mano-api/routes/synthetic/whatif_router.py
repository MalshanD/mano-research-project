"""
What-If Lifestyle Simulator — Router

Lets users ask: "What if I changed my lifestyle?"
Compares baseline trajectory vs modified trajectory side-by-side.

SAFETY: This router uses the EXISTING InterventionService and
RiskPredictionService via dependency injection. No model code is
modified. It only constructs modified input arrays.
"""
from fastapi import APIRouter, HTTPException, Depends
import numpy as np

# --- Schemas ---
from schemas.synthetic.whatif_schema import (
    WhatIfRequest,
    WhatIfResponse,
    TrajectoryDay,
)

# Normalisation constants — needed so slider target values (raw units) are
# scaled to [0, 1] before being blended into the normalised history tensor.
from lib.synthetic.state_parser import (
    _FEATURE_MIN,
    _FEATURE_RANGE,
    _denormalize_dynamic,
    parse_patient_state,
    clamp_simulated_vitals,
)

from schemas.synthetic.simulation_schema import (
    RiskPredictionResponse,
    RiskLevel,
)

# --- Services ---
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService

from core.logging import get_logger

logger = get_logger("whatif_router")

router = APIRouter()


# --- Dependency Injection (same singletons as simulation_router) ---
def get_intervention_service():
    return InterventionService()

def get_risk_service():
    return RiskPredictionService()


# --- Helper: Blend patient history toward lifestyle targets ---
def blend_toward_targets(dynamic_np: np.ndarray, targets, blend_days: int) -> np.ndarray:
    """
    Creates a modified copy of the 7-day history where the last `blend_days`
    are gradually shifted toward the user's target values.

    The blending is LINEAR: earlier days are barely changed, the most recent
    day is closest to the target. This simulates a gradual lifestyle change,
    not an abrupt jump — which is more realistic and produces better Seq2Seq output.

    Args:
        dynamic_np: shape (1, 7, 4) — already normalised to [0, 1] by parse_patient_state
        targets: LifestyleTargets pydantic model (values in RAW units from the frontend slider)
        blend_days: how many of the last days to modify (1-7)

    Returns:
        modified copy of dynamic_np, shape (1, 7, 4) — still in normalised [0, 1] space

    IMPORTANT — target normalisation:
        ``dynamic_np`` is in [0, 1] (normalised) space after parse_patient_state.
        The user's lifestyle targets arrive in raw units (e.g. sleep_hours=9.0,
        heart_rate=65). We MUST normalise those targets to [0, 1] before blending
        them into the history array, otherwise the interpolation mixes incompatible
        scales and produces nonsensical inputs for the Seq2Seq model.
    """
    modified = dynamic_np.copy()

    # Raw target values from the frontend slider (may be None if the user left
    # a slider unchanged).
    raw_targets = [
        targets.sleep_hours,    # Index 0
        targets.sleep_quality,  # Index 1
        targets.heart_rate,     # Index 2
        targets.stress_level,   # Index 3
    ]

    # Normalise each raw target to [0, 1] using the training-time MinMax constants.
    # _FEATURE_MIN / _FEATURE_RANGE are imported from state_parser so the
    # transform is always in sync with parse_patient_state.
    normalised_targets = [
        (raw_targets[i] - float(_FEATURE_MIN[i])) / float(_FEATURE_RANGE[i])
        if raw_targets[i] is not None else None
        for i in range(4)
    ]

    # Only blend the last `blend_days` days
    start_day = 7 - blend_days

    for day_idx in range(start_day, 7):
        # How far into the blend window (0.0 = barely changed, 1.0 = fully at target)
        progress = (day_idx - start_day + 1) / blend_days

        for feat_idx, norm_target in enumerate(normalised_targets):
            if norm_target is not None:
                original_val = modified[0, day_idx, feat_idx]
                # Linear interpolation in normalised space: original → normalised_target
                modified[0, day_idx, feat_idx] = (
                    original_val * (1 - progress) + norm_target * progress
                )

    return modified


# --- Helper: Convert numpy trajectory to response objects ---
def numpy_to_trajectory(future_np: np.ndarray) -> list:
    """Converts a (1, 7, 4) normalised numpy array to TrajectoryDay objects.

    The Seq2Seq model outputs values in [0, 1] (normalised space).  We
    denormalise back to real-world units before serialising so the frontend
    charts display human-readable values (e.g. 8.5 hrs sleep, 72 bpm HR).
    """
    # Denormalise: [0, 1] → raw units ([0,12], [0,1], [50,120], [0,1])
    future_raw = _denormalize_dynamic(future_np)

    trajectory = []
    for i in range(future_raw.shape[1]):
        row = future_raw[0, i]
        trajectory.append(TrajectoryDay(
            day=i + 1,
            sleep_hours=round(float(np.clip(row[0], 0, 24)), 2),
            sleep_quality=round(float(np.clip(row[1], 0, 1)), 3),
            heart_rate=round(float(np.clip(row[2], 40, 200)), 1),
            stress_level=round(float(np.clip(row[3], 0, 1)), 3),
        ))
    return trajectory


# --- Helper: Generate improvement summary ---
def generate_summary(baseline_risk: dict, modified_risk: dict, targets) -> str:
    """Creates a human-readable summary of the what-if comparison."""
    risk_map = {0: "Low", 1: "Medium", 2: "High"}

    base_class = risk_map[baseline_risk["risk_class"]]
    mod_class = risk_map[modified_risk["risk_class"]]

    delta = baseline_risk["probabilities"][2] - modified_risk["probabilities"][2]

    # Build change description
    changes = []
    if targets.sleep_hours is not None:
        changes.append(f"sleep to {targets.sleep_hours}h")
    if targets.sleep_quality is not None:
        changes.append(f"sleep quality to {targets.sleep_quality:.0%}")
    if targets.heart_rate is not None:
        changes.append(f"resting HR to {targets.heart_rate:.0f} bpm")
    if targets.stress_level is not None:
        changes.append(f"stress to {targets.stress_level:.0%}")

    change_str = ", ".join(changes) if changes else "no changes"

    if delta > 0.05:
        tone = f"Adjusting {change_str} shows a projected improvement. High-risk probability decreases by {delta:.1%}."
    elif delta < -0.05:
        tone = f"Adjusting {change_str} may not improve outcomes. High-risk probability increases by {abs(delta):.1%}."
    else:
        tone = f"Adjusting {change_str} shows minimal projected impact on risk level."

    if base_class != mod_class:
        tone += f" Risk class shifts from {base_class} to {mod_class}."

    return tone


# === ENDPOINT ===

@router.post("/what_if", response_model=WhatIfResponse)
async def what_if_simulate(
    request: WhatIfRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """
    Simulates the effect of lifestyle changes on projected health outcomes.

    Flow:
    1. Parse patient state into numpy arrays
    2. Create a modified copy with lifestyle targets blended in
    3. Run Seq2Seq on BOTH original and modified (Control intervention)
    4. Run LSTM risk prediction on both projected futures
    5. Return side-by-side comparison
    """
    logger.info("whatif_request", blend_days=request.blend_days)

    # Step 1: Parse the patient state
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    # Step 2: Create modified history
    modified_dyn_np = blend_toward_targets(
        dyn_np,
        request.lifestyle_targets,
        request.blend_days
    )

    try:
        # Step 3: Simulate BOTH trajectories with Control intervention (no treatment)
        # Control = intervention_type 0, minimal intensity
        baseline_future_np = int_service.simulate_outcome(dyn_np, 0, 0.1)
        modified_future_np = int_service.simulate_outcome(modified_dyn_np, 0, 0.1)
    except Exception as e:
        logger.error("whatif_simulation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    # Step 4: Predict risk on both futures
    baseline_risk = risk_service.predict(baseline_future_np, stat_np)
    modified_risk = risk_service.predict(modified_future_np, stat_np)

    # Step 5: Convert to response objects
    risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}

    base_risk_resp = RiskPredictionResponse(
        current_risk_class=risk_map[baseline_risk["risk_class"]],
        confidence=baseline_risk["confidence"],
        probabilities=baseline_risk["probabilities"],
    )
    mod_risk_resp = RiskPredictionResponse(
        current_risk_class=risk_map[modified_risk["risk_class"]],
        confidence=modified_risk["confidence"],
        probabilities=modified_risk["probabilities"],
    )

    delta = baseline_risk["probabilities"][2] - modified_risk["probabilities"][2]
    summary = generate_summary(
        baseline_risk, modified_risk, request.lifestyle_targets
    )

    logger.info(
        "whatif_complete",
        risk_delta=round(delta, 4),
        baseline_class=baseline_risk["risk_class"],
        modified_class=modified_risk["risk_class"],
    )

    return WhatIfResponse(
        baseline_trajectory=numpy_to_trajectory(baseline_future_np),
        modified_trajectory=numpy_to_trajectory(modified_future_np),
        baseline_risk=base_risk_resp,
        modified_risk=mod_risk_resp,
        risk_delta=round(delta, 4),
        improvement_summary=summary,
    )
