from fastapi import APIRouter, HTTPException, Depends
from typing import List
import numpy as np

# --- IMPORTS: SCHEMAS ---
# These enforce strict data types for inputs and outputs.
# If the frontend sends bad data, FastAPI rejects it before it reaches our logic.
from schemas.synthetic.simulation_schema import (
    SimulationRequest,
    SimulationResponse,
    PatientState,
    PrescriptionResponse,
    RiskLevel,
    DayVitals,
    RiskPredictionResponse
)

# --- IMPORTS: SERVICES ---
# We import the Singleton services that hold the loaded ML models in memory.
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
# Canonical state-tensor helpers — single source of truth for feature order
# and clamp ranges across every synthetic router.
from lib.synthetic.state_parser import (
    parse_patient_state,
    clamp_simulated_vitals,
)

# Initialize the Router
router = APIRouter()

# --- DEPENDENCY INJECTION ---
# These helpers ensure we get the same instance of the service (Singleton pattern).
# This prevents reloading the heavy ML models on every single request.
def get_intervention_service():
    return InterventionService()

def get_risk_service():
    return RiskPredictionService()

# NOTE: parse_patient_state and clamp_simulated_vitals previously lived here as
# free functions duplicated in every synthetic router. They now live in
# lib/synthetic/state_parser.py. If you want to change feature order or clamp
# ranges, edit that module — NOT this router — and confirm the frozen model
# checkpoints still expect the new order.
    return vitals_list

# --- ENDPOINT 1: DIAGNOSIS ---
@router.post("/predict_risk", response_model=RiskPredictionResponse)
async def predict_risk(
    state: PatientState,
    risk_service: RiskPredictionService = Depends(get_risk_service)
):
    """
    Diagnose the patient's CURRENT state using the Hybrid LSTM.
    """
    # Step 1: Convert JSON to Numpy
    dyn_np, stat_np = parse_patient_state(state)

    try:
        # Step 2: Run Inference (Service Layer)
        # This calls the LSTM model on the GPU/CPU.
        result = risk_service.predict(dyn_np, stat_np)
    except Exception as e:
        # If the model crashes (e.g., shape mismatch), return a 500 error.
        raise HTTPException(status_code=500, detail=str(e))

    # Step 3: Map integer class (0, 1, 2) to readable Enum (Low, Medium, High)
    risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}

    # Step 4: Return formatted response matching the Schema
    return RiskPredictionResponse(
        current_risk_class=risk_map[result['risk_class']],
        confidence=result['confidence'],
        probabilities=result['probabilities']
    )

# --- ENDPOINT 2: SIMULATION (THE "WHAT IF" ENGINE) ---
@router.post("/simulate_intervention", response_model=SimulationResponse)
async def simulate_intervention(
    request: SimulationRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service)
):
    """
    Orchestrates the full loop:
    Current State -> Simulate Intervention (Seq2Seq) -> Predict Future Risk (LSTM).
    """
    # Step 1: Parse the patient state from the request
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    # Step 2: Get the BASELINE Risk (Before Intervention)
    # We need this to calculate the "Risk Reduction Score" later.
    base_risk = risk_service.predict(dyn_np, stat_np)

    try:
        # Step 3: Run the Physics Simulation (Seq2Seq Model)
        # This asks: "If we apply this intervention, what does the next 7 days look like?"
        # Output is a numpy array of shape (1, 7, 4)
        future_dyn_np = int_service.simulate_outcome(
            dyn_np,
            request.intervention_type.value, # Enum to Int (e.g., CBT -> 2)
            request.intensity
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    # Step 4: Predict FUTURE Risk (LSTM Model)
    # We feed the *simulated* future data into the diagnostic model.
    future_risk = risk_service.predict(future_dyn_np, stat_np)

    # Step 5: Convert Simulated Data back to Pydantic objects (with clamping)
    future_vitals_list = clamp_simulated_vitals(future_dyn_np)

    risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}

    # Step 6: Construct the Analysis Response
    return SimulationResponse(
        original_risk=RiskPredictionResponse(
            current_risk_class=risk_map[base_risk['risk_class']],
            confidence=base_risk['confidence'],
            probabilities=base_risk['probabilities']
        ),
        projected_risk=RiskPredictionResponse(
            current_risk_class=risk_map[future_risk['risk_class']],
            confidence=future_risk['confidence'],
            probabilities=future_risk['probabilities']
        ),
        future_vitals=future_vitals_list,
        # Calculate improvement: (High Risk Prob Before) - (High Risk Prob After)
        # Positive score means risk went down.
        risk_reduction_score=base_risk['probabilities'][2] - future_risk['probabilities'][2]
    )

# --- ENDPOINT 3: AI PRESCRIPTION ---
@router.post("/prescribe_ai", response_model=PrescriptionResponse)
async def prescribe_ai(
    state: PatientState,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service)
):
    """
    Consults the PPO Agent (The Doctor) to find the optimal treatment.
    Also runs a risk assessment so the frontend can display the current risk context.
    """
    dyn_np, stat_np = parse_patient_state(state)

    # Run current risk assessment
    risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}
    try:
        risk_result = risk_service.predict(dyn_np, stat_np)
        current_risk = RiskPredictionResponse(
            current_risk_class=risk_map[risk_result['risk_class']],
            confidence=risk_result['confidence'],
            probabilities=risk_result['probabilities']
        )
    except Exception:
        current_risk = None

    # The PPO agent expects a flat vector of size 48 (28 dynamic + 20 static)
    dyn_flat = dyn_np.flatten()
    stat_flat = stat_np.flatten()

    try:
        # Ask the Agent
        result = int_service.get_prescription(dyn_flat, stat_flat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Map the Agent's numeric output ID to a human-readable string
    intervention_names = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]

    # Safety check in case the model hallucinates an ID out of bounds (rare but possible)
    if 0 <= result['intervention_id'] < len(intervention_names):
        name = intervention_names[result['intervention_id']]
    else:
        name = "Unknown Protocol"

    return PrescriptionResponse(
        recommended_intervention=name,
        recommended_intensity=result['intensity'],
        confidence=result.get('confidence', 0.0),
        current_risk=current_risk,
        reasoning="Prescription optimized to minimize long-term risk probability."
    )


# --- ENDPOINT 4: BATCH SIMULATION (COMPARE ALL INTERVENTIONS) ---
from schemas.synthetic.batch_schema import (
    BatchSimulationRequest,
    BatchSimulationResponse,
    InterventionComparison,
)

INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]

@router.post("/simulate_batch", response_model=BatchSimulationResponse)
async def simulate_batch(
    request: BatchSimulationRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """
    Run ALL 5 interventions on a patient and compare results.
    Returns them ranked by risk reduction score (best first).
    """
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    # Get baseline risk
    base_risk = risk_service.predict(dyn_np, stat_np)
    risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}

    baseline_response = RiskPredictionResponse(
        current_risk_class=risk_map[base_risk['risk_class']],
        confidence=base_risk['confidence'],
        probabilities=base_risk['probabilities'],
    )

    # Run each intervention
    comparisons = []
    for intervention_id in range(5):
        try:
            future_dyn_np = int_service.simulate_outcome(
                dyn_np, intervention_id, request.intensity
            )
            future_risk = risk_service.predict(future_dyn_np, stat_np)

            # Convert future vitals (clamped to valid ranges)
            future_vitals = clamp_simulated_vitals(future_dyn_np)

            comparisons.append(InterventionComparison(
                intervention_name=INTERVENTION_NAMES[intervention_id],
                intervention_id=intervention_id,
                intensity=request.intensity,
                original_risk=baseline_response,
                projected_risk=RiskPredictionResponse(
                    current_risk_class=risk_map[future_risk['risk_class']],
                    confidence=future_risk['confidence'],
                    probabilities=future_risk['probabilities'],
                ),
                future_vitals=future_vitals,
                risk_reduction_score=base_risk['probabilities'][2] - future_risk['probabilities'][2],
            ))
        except Exception as e:
            # Log the failure but continue with remaining interventions
            from core.logging import get_logger
            get_logger("batch_sim").warning(
                "intervention_skipped", intervention_id=intervention_id, error=str(e)
            )
            continue

    # Sort by risk reduction (highest reduction first = best intervention)
    comparisons.sort(key=lambda c: c.risk_reduction_score, reverse=True)

    best = comparisons[0] if comparisons else None

    return BatchSimulationResponse(
        patient_baseline_risk=baseline_response,
        comparisons=comparisons,
        best_intervention=best.intervention_name if best else "None",
        best_risk_reduction=best.risk_reduction_score if best else 0.0,
    )
