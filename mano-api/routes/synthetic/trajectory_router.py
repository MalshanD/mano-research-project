"""
Trajectory forecasting router.

Thin HTTP layer over ``lib/synthetic/trajectory_service.py``. The route:

1. Parses the patient payload via the canonical ``state_parser``.
2. Delegates horizon-extrapolation + per-day risk to ``forecast_trajectory``.
3. Maps the service's dict result into the ``TrajectoryResponse`` pydantic schema.
4. Publishes a ``c1.trajectory.computed`` event on the in-process bus so
   downstream subscribers (future-self narrative, dashboard digests) can
   react without polling.

All math lives in the service. Keeping the router boring makes it trivial
to add transport-level concerns later (rate-limiting, caching, replay) without
touching clinical logic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from lib.infra.event_bus import Topics, get_event_bus
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import parse_patient_state
from lib.synthetic.trajectory_service import forecast_trajectory
from schemas.synthetic.simulation_schema import InterventionType
from schemas.synthetic.trajectory_schema import (
    DayForecast,
    TrajectoryRequest,
    TrajectoryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton DI — same pattern as simulation_router. Prevents reload of the
# ~800MB frozen checkpoints on every request.
def get_intervention_service() -> InterventionService:
    return InterventionService()


def get_risk_service() -> RiskPredictionService:
    return RiskPredictionService()


_INTERVENTION_NAMES = {
    InterventionType.CONTROL: "Control",
    InterventionType.WELLNESS_APP: "Wellness App",
    InterventionType.CBT: "CBT",
    InterventionType.EXERCISE: "Exercise",
    InterventionType.MEDICATION: "Medication",
}


def _build_day_forecast(day: Dict[str, Any]) -> DayForecast:
    """Adapt one service-layer day dict into the Pydantic response model."""
    return DayForecast(
        day_index=day["day_index"],
        vitals=day["vitals"],
        risk_class=day["risk_class"],
        risk_confidence=day["risk_confidence"],
        risk_probabilities=day["risk_probabilities"],
        risk_probability_std=day.get("risk_probability_std"),
        predictive_entropy=day.get("predictive_entropy"),
        mutual_information=day.get("mutual_information"),
    )


@router.post("/forecast", response_model=TrajectoryResponse)
async def forecast(
    request: TrajectoryRequest,
    int_service: InterventionService = Depends(get_intervention_service),
    risk_service: RiskPredictionService = Depends(get_risk_service),
) -> TrajectoryResponse:
    """Produce a multi-horizon risk trajectory with optional uncertainty bands.

    The forecast horizon is clipped to the 7..28 day range enforced by the
    schema. Beyond day 7 the Seq2Seq is rolled forward recursively; a note
    to that effect is surfaced in the response ``notes`` so the UI can fade
    confidence visually past the native horizon.
    """
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    try:
        result = forecast_trajectory(
            dynamic_np=dyn_np,
            static_np=stat_np,
            intervention_type=int(request.intervention_type.value),
            intensity=float(request.intensity),
            horizon_days=int(request.horizon_days),
            uncertainty_samples=int(request.uncertainty_samples),
            intervention_service=int_service,
            risk_service=risk_service,
        )
    except ValueError as exc:
        # Bubble schema-level preconditions (e.g. horizon < window) as 422 —
        # they represent user input that bypassed Pydantic's static checks.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        # Model not loaded. Treat as service-unavailable rather than 500 —
        # matches how /health flags a "degraded" state.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover — defensive catch-all
        logger.exception("trajectory_forecast_failed")
        raise HTTPException(status_code=500, detail=f"Trajectory forecast failed: {exc}") from exc

    forecasts = [_build_day_forecast(d) for d in result["forecasts"]]
    intervention_label = _INTERVENTION_NAMES.get(
        request.intervention_type, request.intervention_type.name.title()
    )

    response = TrajectoryResponse(
        horizon_days=result["horizon_days"],
        intervention=intervention_label,
        intensity=float(request.intensity),
        forecasts=forecasts,
        peak_risk_day=result.get("peak_risk_day"),
        peak_risk_class=result.get("peak_risk_class"),
        trajectory_shape=result["trajectory_shape"],
        notes=result.get("notes", []),
    )

    # Fire-and-forget event. Any subscriber failure must never break the API
    # response — the bus swallows publish errors internally.
    try:
        await get_event_bus().publish(
            Topics.TRAJECTORY_COMPUTED,
            {
                "horizon_days": response.horizon_days,
                "intervention": response.intervention,
                "intensity": response.intensity,
                "peak_risk_day": response.peak_risk_day,
                "peak_risk_class": response.peak_risk_class.value if response.peak_risk_class else None,
                "trajectory_shape": response.trajectory_shape,
            },
        )
    except Exception:  # pragma: no cover
        logger.debug("trajectory_event_publish_failed", exc_info=True)

    return response
