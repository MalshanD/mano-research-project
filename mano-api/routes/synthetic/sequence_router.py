"""
Intervention Sequencing — Router

Chains Seq2Seq simulations: the 7-day output of step N becomes
the input for step N+1. This models multi-phase treatment plans.

Example sequence: CBT (7d) → Exercise (7d) → Wellness App (7d)
Total trajectory: 21 days with risk evaluated at each milestone.

HOW IT WORKS:
1. Parse patient state → get initial 7-day history
2. For each step:
   a. Run Seq2Seq(current_history, intervention, intensity) → 7-day future
   b. Predict risk on that future
   c. The output becomes the NEW history for the next step
3. Return per-step results + total risk reduction

SAFETY: Reuses InterventionService.simulate_outcome() and
RiskPredictionService.predict() directly. No model changes.
"""
from fastapi import APIRouter, HTTPException, Depends
import numpy as np

# --- Schemas ---
from schemas.synthetic.sequence_schema import (
    SequenceRequest,
    SequenceResponse,
    StepResult,
)
from schemas.synthetic.simulation_schema import (
    RiskPredictionResponse,
    RiskLevel,
)

# --- Reuse existing helpers ---
from routes.synthetic.simulation_router import (
    parse_patient_state,
    clamp_simulated_vitals,
)

# --- Services ---
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService

from core.logging import get_logger

logger = get_logger("sequence_router")

router = APIRouter()

INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]
RISK_MAP = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}


def get_intervention_service():
    return InterventionService()

def get_risk_service():
    return RiskPredictionService()


def build_risk_response(risk_result: dict) -> RiskPredictionResponse:
    return RiskPredictionResponse(
        current_risk_class=RISK_MAP[risk_result["risk_class"]],
        confidence=risk_result["confidence"],
        probabilities=risk_result["probabilities"],
    )


@router.post("/run_sequence", response_model=SequenceResponse)
async def run_sequence(
    request: SequenceRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """
    Chains Seq2Seq simulations to model multi-step treatment plans.
    Each step's output feeds into the next step's input.
    """
    logger.info("sequence_request", num_steps=len(request.steps))

    # Step 1: Parse initial patient state
    current_dyn, stat_np = parse_patient_state(request.patient_state)

    # Step 2: Get baseline risk
    baseline_risk = risk_service.predict(current_dyn, stat_np)
    baseline_high = baseline_risk["probabilities"][2]

    step_results = []
    prev_high = baseline_high

    # Step 3: Chain simulations
    for i, step in enumerate(request.steps):
        int_name = (
            INTERVENTION_NAMES[step.intervention_type]
            if 0 <= step.intervention_type < len(INTERVENTION_NAMES)
            else "Unknown"
        )

        try:
            # Simulate this step
            future_dyn = int_service.simulate_outcome(
                current_dyn, step.intervention_type, step.intensity
            )

            # Predict risk on the output
            step_risk = risk_service.predict(future_dyn, stat_np)
            step_high = step_risk["probabilities"][2]

            # Convert simulated data to vitals for frontend
            vitals_list = clamp_simulated_vitals(future_dyn)

            step_results.append(StepResult(
                step_number=i + 1,
                intervention_name=int_name,
                intensity=round(step.intensity, 2),
                projected_vitals=vitals_list,
                risk_after=build_risk_response(step_risk),
                risk_delta_from_previous=round(prev_high - step_high, 4),
            ))

            # The output becomes the next step's input
            current_dyn = future_dyn
            prev_high = step_high

        except Exception as e:
            logger.error("sequence_step_failed", step=i + 1, error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Simulation failed at step {i + 1} ({int_name}): {str(e)}"
            )

    # Step 4: Final risk
    final_risk = step_results[-1].risk_after if step_results else build_risk_response(baseline_risk)
    final_high = step_results[-1].risk_after.probabilities[2] if step_results else baseline_high
    total_reduction = baseline_high - final_high

    # Step 5: Build summary
    step_names = [f"{s.intervention_name} ({s.intensity:.0%})" for s in step_results]
    sequence_str = " → ".join(step_names)

    if total_reduction > 0.05:
        tone = "significant improvement"
    elif total_reduction > 0:
        tone = "modest improvement"
    else:
        tone = "no net improvement"

    summary = (
        f"Sequence: {sequence_str}. "
        f"Over {len(step_results) * 7} days, "
        f"High-risk probability moves from {baseline_high:.1%} to {final_high:.1%} "
        f"({tone}, Δ = {total_reduction:+.1%})."
    )

    logger.info(
        "sequence_complete",
        num_steps=len(step_results),
        total_reduction=round(total_reduction, 4),
    )

    return SequenceResponse(
        baseline_risk=build_risk_response(baseline_risk),
        steps=step_results,
        final_risk=final_risk,
        total_risk_reduction=round(total_reduction, 4),
        summary=summary,
    )
