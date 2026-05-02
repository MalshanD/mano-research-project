"""
Next-Best-Action — Router

Full closed-loop AI recommendation system:
1. PPO Agent selects the optimal intervention + intensity
2. Seq2Seq simulates ALL 5 interventions at PPO's intensity
3. LSTM predicts risk for each simulated future
4. All interventions ranked by risk reduction
5. Returns PPO's pick + full comparison evidence

This is the "brain of the system" — it shows PPO, Seq2Seq, and LSTM
working together as a unified intelligence, not just independent models.

SAFETY: Uses existing services via dependency injection. No modifications
to any model or service code. All computation is additive.
"""
from fastapi import APIRouter, HTTPException, Depends
import numpy as np

# --- Schemas ---
from schemas.synthetic.nba_schema import (
    NBAResponse,
    InterventionCandidate,
)
from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
    RiskLevel,
)

# --- Reuse existing helpers ---
from routes.synthetic.simulation_router import parse_patient_state

# --- Services ---
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService

from core.logging import get_logger

logger = get_logger("nba_router")

router = APIRouter()

INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]
RISK_MAP = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}


def get_intervention_service():
    return InterventionService()

def get_risk_service():
    return RiskPredictionService()


def build_risk_response(risk_result: dict) -> RiskPredictionResponse:
    """Convert raw risk dict to Pydantic response."""
    return RiskPredictionResponse(
        current_risk_class=RISK_MAP[risk_result["risk_class"]],
        confidence=risk_result["confidence"],
        probabilities=risk_result["probabilities"],
    )


@router.post("/recommend", response_model=NBAResponse)
async def next_best_action(
    state: PatientState,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """
    Closed-loop recommendation: PPO picks → Seq2Seq simulates all options
    → LSTM evaluates → ranked comparison returned.
    """
    logger.info("nba_request")

    # Step 1: Parse state
    dyn_np, stat_np = parse_patient_state(state)

    # Step 2: Get baseline risk
    baseline_risk = risk_service.predict(dyn_np, stat_np)
    baseline_high_prob = baseline_risk["probabilities"][2]

    # Step 3: Ask PPO Agent for its recommendation
    dyn_flat = dyn_np.flatten()
    stat_flat = stat_np.flatten()

    try:
        ppo_result = int_service.get_prescription(dyn_flat, stat_flat)
    except Exception as e:
        logger.error("nba_ppo_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"PPO Agent failed: {str(e)}")

    ppo_intervention_id = ppo_result["intervention_id"]
    ppo_intensity = ppo_result["intensity"]

    # Step 4: Simulate ALL interventions at PPO's intensity
    candidates = []

    for int_id in range(len(INTERVENTION_NAMES)):
        try:
            # Use PPO's intensity for fair comparison
            future_np = int_service.simulate_outcome(dyn_np, int_id, ppo_intensity)
            future_risk = risk_service.predict(future_np, stat_np)

            risk_reduction = baseline_high_prob - future_risk["probabilities"][2]

            candidates.append({
                "intervention_id": int_id,
                "name": INTERVENTION_NAMES[int_id],
                "intensity": ppo_intensity,
                "risk_result": future_risk,
                "risk_reduction": risk_reduction,
            })
        except Exception as e:
            logger.warning("nba_sim_failed", intervention=INTERVENTION_NAMES[int_id], error=str(e))
            continue

    # Step 5: Rank by risk reduction (highest = best)
    candidates.sort(key=lambda c: c["risk_reduction"], reverse=True)

    candidate_responses = []
    for rank, c in enumerate(candidates, 1):
        candidate_responses.append(InterventionCandidate(
            intervention_id=c["intervention_id"],
            intervention_name=c["name"],
            intensity=round(c["intensity"], 2),
            projected_risk=build_risk_response(c["risk_result"]),
            risk_reduction=round(c["risk_reduction"], 4),
            rank=rank,
        ))

    # Step 6: Check if PPO agrees with simulation ranking
    top_sim = candidates[0] if candidates else None
    is_ppo_top = top_sim and top_sim["intervention_id"] == ppo_intervention_id

    ppo_name = (
        INTERVENTION_NAMES[ppo_intervention_id]
        if 0 <= ppo_intervention_id < len(INTERVENTION_NAMES)
        else "Unknown"
    )

    # Step 7: Build reasoning
    if is_ppo_top:
        reasoning = (
            f"The PPO Agent recommends {ppo_name} at {ppo_intensity:.0%} intensity. "
            f"This choice is confirmed by simulation — it produces the best projected "
            f"risk reduction ({top_sim['risk_reduction']:.1%}) across all interventions."
        )
        confidence_note = (
            "High confidence: PPO recommendation and simulation ranking agree."
        )
    elif top_sim:
        reasoning = (
            f"The PPO Agent recommends {ppo_name} at {ppo_intensity:.0%} intensity. "
            f"However, simulation shows {top_sim['name']} may produce better outcomes "
            f"({top_sim['risk_reduction']:.1%} vs "
            f"{next((c['risk_reduction'] for c in candidates if c['intervention_id'] == ppo_intervention_id), 0):.1%}). "
            f"Consider both options."
        )
        confidence_note = (
            f"Mixed signals: PPO recommends {ppo_name}, "
            f"but simulation favors {top_sim['name']}. "
            f"The PPO may be optimizing for long-term factors not captured in 7-day simulation."
        )
    else:
        reasoning = "Unable to complete simulation comparison."
        confidence_note = "Simulation incomplete — rely on PPO recommendation."

    logger.info(
        "nba_complete",
        ppo_pick=ppo_name,
        sim_top=top_sim["name"] if top_sim else "none",
        agreement=is_ppo_top,
    )

    return NBAResponse(
        recommended_intervention=ppo_name,
        recommended_intensity=round(ppo_intensity, 2),
        is_ppo_top_ranked=is_ppo_top,
        baseline_risk=build_risk_response(baseline_risk),
        candidates=candidate_responses,
        reasoning=reasoning,
        confidence_note=confidence_note,
    )
