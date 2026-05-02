"""HTTP route layer for the Proactive Trajectory Alerting service.

Exposes the alert tier + history endpoints. The existing
``/api/v1/trajectory/forecast`` route remains untouched — these
endpoints sit alongside it.

UI hint: every response carries ``severity_color``, ``icon_hint``,
``microcopy``, ``recommended_action`` and CTA fields so the chip can
be rendered with no business logic on the client.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from core.errors import ErrorCode, MANOAPIError
from lib.synthetic import trajectory_alert_service
from schemas.synthetic.simulation_schema import PatientState
from schemas.synthetic.trajectory_alert_schema import (
    TrajectoryAlertHistory,
    TrajectoryAlertRequest,
    TrajectoryAlertStatus,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class _AlertStatusRequest(BaseModel):
    patient_id: str
    patient_state: PatientState
    options: TrajectoryAlertRequest | None = None


@router.post(
    "/alert-status",
    response_model=TrajectoryAlertStatus,
    summary="Compute the current trajectory-alert tier for a patient",
    description=(
        "Runs a multi-horizon LSTM forecast on a phantom-extrapolated "
        "vital window and returns the alert tier (OK | WATCH | WARNING "
        "| CRITICAL) plus UI render hints. Persists the result to the "
        "patient's alert history for the trend chart endpoint."
    ),
)
async def alert_status(payload: _AlertStatusRequest) -> TrajectoryAlertStatus:
    try:
        return trajectory_alert_service.compute_alert(
            patient_id=payload.patient_id,
            patient_state=payload.patient_state,
            request=payload.options,
        )
    except RuntimeError as exc:
        logger.error("trajectory_alert_model_unavailable", extra={"error": str(exc)})
        raise MANOAPIError(
            code=ErrorCode.MODEL_UNAVAILABLE,
            message=(
                "Hybrid LSTM not loaded — trajectory alerting requires the "
                "frozen risk model to be live. Check /health."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


@router.get(
    "/history/{patient_id}",
    response_model=TrajectoryAlertHistory,
    summary="Recent alert-tier history for a patient",
    description=(
        "Returns up to ``days_lookback`` most-recent alert records for "
        "the trend chart. Backed by an in-memory ring buffer; production "
        "deployments swap in a Redis-backed store via "
        "``trajectory_alert_service.set_history_store``."
    ),
)
async def alert_history(patient_id: str, days_lookback: int = 30) -> TrajectoryAlertHistory:
    days_lookback = max(1, min(days_lookback, 90))
    return trajectory_alert_service.get_history(patient_id, days_lookback)
