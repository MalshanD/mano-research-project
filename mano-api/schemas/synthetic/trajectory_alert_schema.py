"""
Pydantic schemas for the Proactive Trajectory Alerting layer.

Builds on the existing one-shot ``trajectory_router`` by adding alert
tiers (WATCH / WARNING / CRITICAL), a per-patient history view, and
event-bus emission. The alert tier is the single signal a clinician's
dashboard renders as a coloured chip — everything else is supporting
detail.

UI contract
-----------
The frontend treats ``severity_color``, ``microcopy``, ``icon_hint``,
``cta_label`` and ``cta_endpoint`` as authoritative — those come from
the backend so a UX update doesn't require a frontend rebuild.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AlertTier(str, Enum):
    """Four-tier alert severity matching the guideline's threshold model."""

    OK = "ok"            # nothing to surface
    WATCH = "watch"      # trend deteriorating, no breach predicted
    WARNING = "warning"  # breach predicted within 3 days
    CRITICAL = "critical"  # breach predicted within 48 hours


class TrajectoryDayForecast(BaseModel):
    """One projected day on the alert horizon."""

    day_offset: int = Field(..., ge=0, le=14, description="0 = today.")
    high_risk_probability: float = Field(..., ge=0.0, le=1.0)
    risk_class: str = Field(..., description="Low | Medium | High")


class TrajectoryAlertStatus(BaseModel):
    """Top-level alert payload for one patient."""

    patient_id: str
    tier: AlertTier
    breach_day: Optional[int] = Field(
        None,
        description="Day-offset at which the trajectory is projected to "
                    "exceed the High-risk class. None when no breach is "
                    "projected within the horizon.",
    )
    horizon_days: int = Field(7, ge=1, le=14)
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence in the forecast — 1 minus the std-dev of "
                    "the day-offset risks. Used to dampen alerts when the "
                    "model is uncertain.",
    )

    forecast: List[TrajectoryDayForecast]
    current_high_risk_probability: float
    trend_direction: str = Field(
        ...,
        description="'improving' | 'stable' | 'deteriorating'",
    )

    # ── UI render hints ──────────────────────────────────────────────
    severity_color: str = Field(
        ...,
        description="Tailwind / hex token for the tier badge. "
                    "e.g. 'emerald-500' | 'amber-500' | 'orange-500' | 'rose-600'.",
    )
    icon_hint: str = Field(
        ...,
        description="lucide-react icon name. e.g. 'check-circle' | "
                    "'eye' | 'alert-triangle' | 'siren'.",
    )
    microcopy: str = Field(
        ...,
        description="One-line user-facing label, suitable for a card header.",
    )
    recommended_action: str = Field(
        ...,
        description="What the user should do next, in plain English.",
    )
    cta_label: Optional[str] = None
    cta_endpoint: Optional[str] = None

    computed_at: datetime
    source: str = Field(
        "live",
        description="'live' or 'cached' — frontend can dim cached cards.",
    )


class TrajectoryAlertHistory(BaseModel):
    """Per-patient alert history for trend visualisation."""

    patient_id: str
    items: List[TrajectoryAlertStatus]
    days_lookback: int


class TrajectoryAlertRequest(BaseModel):
    """Optional payload for the alert endpoint when callers want to scan
    a specific window. Most callers just hit the GET endpoint with the
    patient_id and accept defaults."""

    horizon_days: int = Field(
        7, ge=3, le=14,
        description="Days to forecast forward.",
    )
    breach_threshold: float = Field(
        0.65,
        ge=0.5, le=0.95,
        description="High-risk probability above which a day counts as a "
                    "'breach'. 0.65 is the LSTM's calibrated High-class "
                    "threshold; tighten for tighter alerts.",
    )
