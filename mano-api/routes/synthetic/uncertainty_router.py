"""
MC Dropout Uncertainty — Router

Monte Carlo Dropout for Bayesian uncertainty quantification on the frozen LSTM
risk predictor.

Background
----------
Standard inference runs with ``model.eval()`` — dropout disabled, a single
deterministic prediction. That gives us a point estimate but tells us nothing
about how *confident* the model is in its own answer.

MC Dropout (Gal & Ghahramani, 2016) turns the network into an approximate
Bayesian model by re-enabling dropout at inference time and running N forward
passes. The resulting distribution of predictions lets us report:

* **Predictive entropy**  — total uncertainty (aleatoric + epistemic)
* **Mutual information**  — epistemic uncertainty only (reducible via more data)
* **Stability**           — agreement with the dropout-off point estimate
* **Is reliable?**        — a conservative Boolean for UI gating

Heavy lifting lives in ``lib/synthetic/uncertainty_service.py`` so the
trajectory and counterfactual routers can reuse the exact same statistics.

Safety
------
The service wraps dropout toggling in try/finally. The frozen model's weights
are never modified; only ``nn.Dropout`` submodules are briefly flipped to
train-mode and then restored to eval-mode.
"""

from fastapi import APIRouter, Depends, HTTPException

# --- Schemas ---
from schemas.synthetic.uncertainty_schema import (
    ClassDistribution,
    UncertaintyRequest,
    UncertaintyResponse,
)
from schemas.synthetic.simulation_schema import (
    RiskLevel,
    RiskPredictionResponse,
)

# --- Services ---
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import parse_patient_state
from lib.synthetic.uncertainty_service import predict_with_uncertainty

from core.logging import get_logger

logger = get_logger("uncertainty_router")

router = APIRouter()

RISK_MAP = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}
RISK_NAMES = ("Low", "Medium", "High")


def get_risk_service():
    return RiskPredictionService()


@router.post("/evaluate", response_model=UncertaintyResponse)
async def evaluate_uncertainty(
    request: UncertaintyRequest,
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """Run MC Dropout on the LSTM risk predictor for uncertainty quantification.

    Returns the point estimate plus per-class mean/std/min/max, predictive
    entropy, mutual information, stability, and a plain-English summary.
    """
    if risk_service.model is None:
        raise HTTPException(status_code=503, detail="Risk model not loaded")

    logger.info("mc_dropout_request", n_samples=request.n_samples)

    # Step 1: parse state → tensors
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    # Step 2: get the dropout-OFF point estimate first (service will skip its
    # own when we pass these through)
    point_risk = risk_service.predict(dyn_np, stat_np)

    # Step 3: delegate to the shared uncertainty service
    try:
        result = predict_with_uncertainty(
            model=risk_service.model,
            dynamic_np=dyn_np,
            static_np=stat_np,
            device=risk_service.device,
            n_samples=request.n_samples,
            class_names=RISK_NAMES,
            point_probabilities=point_risk["probabilities"],
            point_class=point_risk["risk_class"],
        )
    except Exception as exc:
        logger.error("mc_dropout_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"MC Dropout failed: {exc}")

    # Step 4: translate the service result into the legacy response schema.
    # Keeping the old shape preserves frontend compatibility.
    class_distributions = [
        ClassDistribution(
            risk_class=cs.class_name,
            mean_probability=cs.mean,
            std_probability=cs.std,
            min_probability=cs.min,
            max_probability=cs.max,
        )
        for cs in result.class_statistics
    ]

    logger.info(
        "mc_dropout_complete",
        point_class=result.point_class,
        stability=result.prediction_stability,
        entropy=result.predictive_entropy,
    )

    return UncertaintyResponse(
        point_estimate=RiskPredictionResponse(
            current_risk_class=RISK_MAP[result.point_class],
            confidence=point_risk["confidence"],
            probabilities=point_risk["probabilities"],
        ),
        n_samples=result.n_samples,
        class_distributions=class_distributions,
        predictive_entropy=result.predictive_entropy,
        mutual_information=result.mutual_information,
        prediction_stability=result.prediction_stability,
        is_reliable=result.is_reliable,
        uncertainty_summary=result.summary,
    )
