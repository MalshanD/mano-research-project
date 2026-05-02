"""
Intervention counterfactual router.

Thin HTTP wrapper over ``lib/synthetic/counterfactual_service.py``. The route:

1. Parses the patient payload via the canonical ``state_parser``.
2. Delegates the dual-arm rollout + comparison metrics to ``run_counterfactual``.
3. Wraps the service dict in the ``CounterfactualResponse`` Pydantic schema.
4. Publishes a ``c1.counterfactual.computed`` event so the passport / narrative
   layers can subscribe without polling.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from lib.infra.event_bus import Topics, get_event_bus
from lib.synthetic.counterfactual_service import run_counterfactual
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import parse_patient_state
from schemas.synthetic.counterfactual_schema import (
    CounterfactualRequest,
    CounterfactualResponse,
    DayRiskSummary,
    InterventionOutcome,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_intervention_service() -> InterventionService:
    return InterventionService()


def get_risk_service() -> RiskPredictionService:
    return RiskPredictionService()


def _to_day_risk(day: Dict[str, Any]) -> DayRiskSummary:
    return DayRiskSummary(
        day_index=day["day_index"],
        risk_class=day["risk_class"],
        risk_confidence=day["risk_confidence"],
        risk_probabilities=day["risk_probabilities"],
        predictive_entropy=day.get("predictive_entropy"),
    )


def _to_outcome(outcome: Dict[str, Any]) -> InterventionOutcome:
    return InterventionOutcome(
        intervention_name=outcome["intervention_name"],
        intervention_type=outcome["intervention_type"],
        intensity=outcome["intensity"],
        horizon_days=outcome["horizon_days"],
        forecast_vitals=outcome["forecast_vitals"],
        risk_trajectory=[_to_day_risk(d) for d in outcome["risk_trajectory"]],
        final_risk_class=outcome["final_risk_class"],
        final_risk_probabilities=outcome["final_risk_probabilities"],
        mean_high_risk_probability=outcome["mean_high_risk_probability"],
        trajectory_shape=outcome["trajectory_shape"],
    )


@router.post("/compare", response_model=CounterfactualResponse)
async def counterfactual_compare(
    request: CounterfactualRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
) -> CounterfactualResponse:
    """Compare two intervention plans (factual vs counterfactual) for the same patient.

    Both arms share identical initial state and static features — the only
    differentiator is the intervention / intensity pair on each arm. This
    isolates the modeled effect of the intervention under the frozen
    Seq2Seq's learned dynamics.
    """
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    try:
        result = run_counterfactual(
            dynamic_np=dyn_np,
            static_np=stat_np,
            factual_intervention=request.factual.intervention_type,
            factual_intensity=float(request.factual.intensity),
            counterfactual_intervention=request.counterfactual.intervention_type,
            counterfactual_intensity=float(request.counterfactual.intensity),
            horizon_days=int(request.horizon_days),
            uncertainty_samples=int(request.uncertainty_samples),
            intervention_service=int_service,
            risk_service=risk_service,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("counterfactual_failed")
        raise HTTPException(status_code=500, detail=f"Counterfactual failed: {exc}") from exc

    response = CounterfactualResponse(
        factual=_to_outcome(result["factual"]),
        counterfactual=_to_outcome(result["counterfactual"]),
        risk_reduction_score=result["risk_reduction_score"],
        risk_reduction_per_day=result["risk_reduction_per_day"],
        counterfactual_is_better=result["counterfactual_is_better"],
        vitals_divergence=result["vitals_divergence"],
        dominant_feature=result.get("dominant_feature"),
        interpretation=result["interpretation"],
        notes=result.get("notes", []),
    )

    try:
        await get_event_bus().publish(
            Topics.COUNTERFACTUAL_COMPUTED,
            {
                "factual_intervention": response.factual.intervention_name,
                "counterfactual_intervention": response.counterfactual.intervention_name,
                "horizon_days": response.factual.horizon_days,
                "risk_reduction_score": response.risk_reduction_score,
                "counterfactual_is_better": response.counterfactual_is_better,
                "dominant_feature": response.dominant_feature,
            },
        )
    except Exception:  # pragma: no cover
        logger.debug("counterfactual_event_publish_failed", exc_info=True)

    return response
