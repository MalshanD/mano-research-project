"""
Proactive Trajectory Alerting.

Wraps the frozen Hybrid LSTM in a multi-horizon forecast that emits an
alert tier — OK / WATCH / WARNING / CRITICAL — every time a patient
state lands. The tier drives downstream behaviour:

  * **OK** — nothing to surface in the patient's dashboard.
  * **WATCH** — trend is deteriorating but no breach is projected
    within the horizon. Render as an amber chip.
  * **WARNING** — a high-risk breach is projected within 3 days. Emit
    on the event bus so Components 2 + 3 can prepare proactive outreach.
  * **CRITICAL** — breach within 48 hours. Emit on the event bus and
    surface as a red banner with a "Start a Guided Therapy Session"
    call-to-action.

Phantom-day algorithm
---------------------
We don't have Seq2Seq here (a deliberate choice — the alert path needs
to stay <100 ms). Instead we extrapolate each of the 4 vital channels
linearly from the most recent 3 days, clamp to physiological ranges,
and run each phantom day through the LSTM. Confidence is 1 minus the
std-dev of the resulting per-day high-risk probabilities.

Persistence
-----------
The history endpoint is backed by an in-memory ring buffer per patient
(default depth 30). Production deployments can swap this for a Redis
list via ``set_history_store(...)`` without touching the alerting
logic. Keeping the store pluggable means tests can supply a mock.

UI render hints
---------------
``severity_color``, ``icon_hint``, ``microcopy``, ``recommended_action``,
``cta_label``, ``cta_endpoint`` are computed server-side so the
frontend can render the chip with no business logic.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

from schemas.synthetic.simulation_schema import PatientState, RiskLevel
from schemas.synthetic.trajectory_alert_schema import (
    AlertTier,
    TrajectoryAlertHistory,
    TrajectoryAlertRequest,
    TrajectoryAlertStatus,
    TrajectoryDayForecast,
)

from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import (
    DYNAMIC_FEATURE_ORDER,
    parse_patient_state,
    vitals_to_matrix,
)

logger = logging.getLogger(__name__)


# Physiological clamp ranges shared with state_parser.
_CLAMPS = {
    0: (0.0, 24.0),    # sleep_hours
    1: (0.0, 1.0),     # sleep_quality
    2: (40.0, 200.0),  # heart_rate
    3: (0.0, 1.0),     # stress_level
}

_RISK_LEVELS: Tuple[str, ...] = ("Low", "Medium", "High")


# ── Pluggable history store ────────────────────────────────────────────────


class _InMemoryHistoryStore:
    """Default per-patient ring buffer. Production: swap for Redis list."""

    def __init__(self, depth: int = 30) -> None:
        self.depth = depth
        self._by_patient: Dict[str, Deque[TrajectoryAlertStatus]] = {}

    def append(self, patient_id: str, item: TrajectoryAlertStatus) -> None:
        buf = self._by_patient.setdefault(
            patient_id, deque(maxlen=self.depth),
        )
        buf.append(item)

    def history(self, patient_id: str, days_lookback: int = 30) -> List[TrajectoryAlertStatus]:
        buf = self._by_patient.get(patient_id, deque())
        return list(buf)[-days_lookback:]


_history_store = _InMemoryHistoryStore()


def set_history_store(store) -> None:
    """Test hook + Redis-swap hook. ``store`` must implement
    ``append(patient_id, item)`` and ``history(patient_id, days_lookback)``."""
    global _history_store
    _history_store = store


# ── Phantom-day extrapolation ──────────────────────────────────────────────


def _extrapolate_phantom_days(
    history_4ch: np.ndarray, horizon_days: int,
) -> np.ndarray:
    """Linearly extrapolate H phantom days from the last 3 history days.

    Input shape: (1, 7, 4). Output shape: (1, H, 4) — clamped per-channel.
    """
    last3 = history_4ch[0, -3:, :]  # (3, 4)
    # Slope per channel = mean step over the last 3 days.
    slopes = np.array([
        (last3[-1, c] - last3[0, c]) / 2.0
        for c in range(4)
    ], dtype=np.float32)

    base = history_4ch[0, -1, :].astype(np.float32)
    phantom = np.zeros((1, horizon_days, 4), dtype=np.float32)
    for d in range(horizon_days):
        for c in range(4):
            raw = base[c] + slopes[c] * (d + 1)
            lo, hi = _CLAMPS[c]
            phantom[0, d, c] = float(np.clip(raw, lo, hi))
    return phantom


# ── Tier classifier ────────────────────────────────────────────────────────


def _trend_direction(curve: List[float]) -> str:
    if len(curve) < 2:
        return "stable"
    delta = curve[-1] - curve[0]
    if delta > 0.05:
        return "deteriorating"
    if delta < -0.05:
        return "improving"
    return "stable"


def _classify_tier(
    breach_day: Optional[int],
    trend: str,
    current_high: float,
) -> AlertTier:
    """Tier rules (ordered, first-match wins):

    1. Breach within 48 h (≤2 days)  → CRITICAL
    2. Breach within 3 days          → WARNING
    3. Trend deteriorating           → WATCH
    4. Otherwise                     → OK
    """
    if breach_day is not None:
        if breach_day <= 2:
            return AlertTier.CRITICAL
        if breach_day <= 3:
            return AlertTier.WARNING
        # Breach beyond 3 days but inside horizon → WATCH (still proactive)
        return AlertTier.WATCH
    if trend == "deteriorating" or current_high >= 0.65:
        return AlertTier.WATCH
    return AlertTier.OK


def _ui_tokens(tier: AlertTier, breach_day: Optional[int], trend: str) -> Dict[str, str]:
    """Tailwind colour, lucide icon, microcopy, recommended action, CTA.

    Centralised here so a UX revision is a one-file diff.
    """
    if tier == AlertTier.CRITICAL:
        return {
            "severity_color": "rose-600",
            "icon_hint": "siren",
            "microcopy": (
                f"Your trajectory is heading sharply higher in the next "
                f"{breach_day or 2} days."
            ),
            "recommended_action": (
                "Open a Guided Therapy Session today, and consider reaching "
                "out to a trusted person."
            ),
            "cta_label": "Start a Guided Therapy Session",
            "cta_endpoint": "/api/v1/therapy/start",
        }
    if tier == AlertTier.WARNING:
        return {
            "severity_color": "orange-500",
            "icon_hint": "alert-triangle",
            "microcopy": "Your trajectory may breach the high-risk band within 3 days.",
            "recommended_action": (
                "Try a short rehearsal of your plan, or run a what-if "
                "simulation to see what helps."
            ),
            "cta_label": "Rehearse my plan",
            "cta_endpoint": "/api/v1/rehearsal/plan",
        }
    if tier == AlertTier.WATCH:
        return {
            "severity_color": "amber-500",
            "icon_hint": "eye",
            "microcopy": (
                "Your trend is gradually heading higher — worth keeping an "
                "eye on."
            ),
            "recommended_action": (
                "Log a short journal entry today, and try to stick to your "
                "current plan."
            ),
            "cta_label": "Open my journal",
            "cta_endpoint": "/api/v1/journal/analyze",
        }
    return {
        "severity_color": "emerald-500",
        "icon_hint": "check-circle",
        "microcopy": "Your projected trajectory is stable.",
        "recommended_action": (
            "Keep doing what's working. A short check-in tomorrow will keep "
            "the picture fresh."
        ),
        "cta_label": "Open my dashboard",
        "cta_endpoint": "/api/v1/dashboard/content",
    }


# ── Main entry point ──────────────────────────────────────────────────────


def compute_alert(
    patient_id: str,
    patient_state: PatientState,
    request: Optional[TrajectoryAlertRequest] = None,
) -> TrajectoryAlertStatus:
    req = request or TrajectoryAlertRequest()
    dyn, stat = parse_patient_state(patient_state)

    # Current risk (today).
    current_pred = RiskPredictionService().predict(dyn, stat)
    current_high = float(current_pred["probabilities"][2])

    # Phantom horizon.
    phantom = _extrapolate_phantom_days(dyn, req.horizon_days)

    # Score each phantom day on a sliding 7-day window of the last 6 history
    # days plus that day. This keeps the LSTM input shape valid and lets the
    # day-offset signal evolve smoothly.
    forecast: List[TrajectoryDayForecast] = []
    breach_day: Optional[int] = None
    history_window = dyn[0].copy()  # (7, 4)
    daily_high: List[float] = []

    for d in range(req.horizon_days):
        new_day = phantom[0, d, :]
        history_window = np.vstack([history_window[1:], new_day[None, :]])
        window_input = history_window[None, :, :].astype(np.float32)
        pred = RiskPredictionService().predict(window_input, stat)
        high_p = float(pred["probabilities"][2])
        risk_cls_idx = int(pred["risk_class"])
        risk_label = _RISK_LEVELS[risk_cls_idx]
        forecast.append(TrajectoryDayForecast(
            day_offset=d + 1,
            high_risk_probability=high_p,
            risk_class=risk_label,
        ))
        daily_high.append(high_p)
        if breach_day is None and high_p >= req.breach_threshold:
            breach_day = d + 1

    trend = _trend_direction([current_high] + daily_high)
    tier = _classify_tier(breach_day, trend, current_high)
    ui = _ui_tokens(tier, breach_day, trend)

    # Confidence = 1 − std-dev across the daily high-risk probabilities.
    if len(daily_high) >= 2:
        confidence = float(max(0.0, 1.0 - statistics.stdev(daily_high)))
    else:
        confidence = 1.0

    status = TrajectoryAlertStatus(
        patient_id=patient_id,
        tier=tier,
        breach_day=breach_day,
        horizon_days=req.horizon_days,
        confidence=confidence,
        forecast=forecast,
        current_high_risk_probability=current_high,
        trend_direction=trend,
        severity_color=ui["severity_color"],
        icon_hint=ui["icon_hint"],
        microcopy=ui["microcopy"],
        recommended_action=ui["recommended_action"],
        cta_label=ui.get("cta_label"),
        cta_endpoint=ui.get("cta_endpoint"),
        computed_at=datetime.now(timezone.utc),
        source="live",
    )

    # Persist + emit.
    _history_store.append(patient_id, status)

    if tier in (AlertTier.WARNING, AlertTier.CRITICAL):
        try:
            from lib.infra.event_bus import Topics, publish as bus_publish
            payload = {
                "patient_id": patient_id,
                "tier": tier.value,
                "breach_day": breach_day,
                "current_high_risk_probability": current_high,
                "computed_at": status.computed_at.isoformat(),
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus_publish(Topics.TRAJECTORY_COMPUTED, payload))
            except RuntimeError:
                pass
        except Exception as exc:  # pragma: no cover — bus is best-effort
            logger.info("trajectory_alert_event_failed", extra={"error": str(exc)})

    return status


def get_history(patient_id: str, days_lookback: int = 30) -> TrajectoryAlertHistory:
    items = _history_store.history(patient_id, days_lookback)
    return TrajectoryAlertHistory(
        patient_id=patient_id,
        items=items,
        days_lookback=days_lookback,
    )
