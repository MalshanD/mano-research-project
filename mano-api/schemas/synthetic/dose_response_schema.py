"""
Pydantic schemas for the Dose-Response Sweep Engine.

Why this exists. PPO returns one (intervention, intensity) pair as the
optimum for the trained reward function — but real users care about
*marginal* benefit per unit of effort. "If I can do 20 minutes a day,
how much better is that than 10? Is going to 30 worth it?" The frozen
PPO can't answer that out of the box.

This engine sweeps the continuous intensity axis for one intervention
type and returns:
  * the projected high-risk probability at each dose,
  * the *marginal* benefit (Δrisk per unit of intensity),
  * the personal "sweet spot" (the dose past which marginal benefit
    starts to drop).

The output is the data needed to render a dose-response curve plus the
single number a clinician can act on.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    InterventionType,
    PatientState,
    RiskLevel,
)


class DoseResponseRequest(BaseModel):
    patient_state: PatientState
    intervention_type: InterventionType
    dose_grid: Optional[List[float]] = Field(
        None,
        description="Optional explicit list of intensities to sweep "
                    "(each in [0.1, 1.0]). When omitted the engine sweeps "
                    "[0.1, 0.2, 0.3, 0.5, 0.7, 0.9] — six points that "
                    "give a smooth curve without burning Seq2Seq passes.",
    )
    horizon_days: int = Field(
        7, ge=3, le=14,
        description="Days projected per dose. Capped at 14 to keep cost bounded.",
    )


class DoseResponsePoint(BaseModel):
    intensity: float = Field(..., ge=0.0, le=1.0)
    projected_high_risk_probability: float = Field(..., ge=0.0, le=1.0)
    delta_vs_baseline: float = Field(
        ...,
        description="projected − baseline. Negative = improvement.",
    )
    delta_vs_previous_dose: Optional[float] = Field(
        None,
        description="projected − previous_dose's projected; the marginal "
                    "step. None for the first point on the grid.",
    )


class DoseResponseCurve(BaseModel):
    baseline_high_risk_probability: float
    baseline_risk_class: RiskLevel
    horizon_days: int
    intervention_type: InterventionType

    points: List[DoseResponsePoint]

    sweet_spot_intensity: Optional[float] = Field(
        None,
        description="The lowest intensity past which the marginal benefit "
                    "from raising the dose drops below "
                    "``diminishing_returns_floor``. None when the curve "
                    "is monotonically improving across the swept range.",
    )
    diminishing_returns_floor: float = Field(
        0.005,
        description="Marginal benefit (per intensity step) below this "
                    "floor counts as 'no further benefit'.",
    )

    interpretation: str

    source: str = "live"
