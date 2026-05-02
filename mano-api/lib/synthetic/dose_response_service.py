"""
Dose-Response Sweep Engine.

For one chosen intervention type, sweep the intensity axis and return
the projected horizon-end high-risk probability at each dose. From that
curve we extract:

  * the marginal Δrisk per dose step, and
  * the lowest intensity past which extra effort stops paying off
    (the "sweet spot").

The PPO agent gives one optimum; a dose-response curve gives a *whole
function*. That's what users want when they're deciding "I can do 15
minutes a day, will that work?". Six Seq2Seq passes per call (at the
default grid), well under 250 ms on the RTX 3050 Ti budget.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

from schemas.synthetic.dose_response_schema import (
    DoseResponseCurve,
    DoseResponsePoint,
    DoseResponseRequest,
)
from schemas.synthetic.simulation_schema import (
    InterventionType,
    PatientState,
    RiskLevel,
)

from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import (
    clamp_simulated_vitals,
    parse_patient_state,
    vitals_to_matrix,
)

logger = logging.getLogger(__name__)


_DEFAULT_GRID: List[float] = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
_RISK_LEVELS = (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)


def _project_horizon(
    starting_history: np.ndarray,
    intervention_id: int,
    intensity: float,
    horizon_days: int,
) -> List["DayVitalsType"]:
    """Project ``horizon_days`` of vitals under one (intervention, intensity)
    pair. Chunks of 7 days with sliding-window history.
    """
    from schemas.synthetic.simulation_schema import DayVitals  # noqa
    rolling = starting_history.copy()
    out: List[DayVitals] = []
    days_left = horizon_days
    while days_left > 0:
        chunk = InterventionService().simulate_outcome(
            rolling, intervention_type=int(intervention_id),
            intensity=float(intensity),
        )
        clamped = clamp_simulated_vitals(chunk)
        take = min(7, days_left)
        out.extend(clamped[:take])
        days_left -= take
        if days_left > 0:
            rolling = vitals_to_matrix(clamped[-7:])
    return out


def _horizon_end_high_risk(
    starting_history,  # List[DayVitals]
    projected,         # List[DayVitals]
    static_features,
) -> float:
    """Score the LSTM on the final 7-day window of the projected horizon."""
    final_window = (list(starting_history) + list(projected))[-7:]
    dyn = vitals_to_matrix(final_window)
    stat = np.array([static_features], dtype=np.float32)
    pred = RiskPredictionService().predict(dyn, stat)
    return float(pred["probabilities"][2])


def _compute_sweet_spot(
    points: List[DoseResponsePoint],
    floor: float,
) -> Optional[float]:
    """The lowest intensity past which raising the dose stops paying off.

    A point qualifies as the sweet spot when the marginal Δ from the
    previous point dips below ``floor`` (the curve flattens). If the
    curve is monotonically improving across the whole range, return None
    (the user could keep going).
    """
    for i in range(1, len(points)):
        prev = points[i - 1]
        cur = points[i]
        # Flattening = the *improvement* from prev to cur is small.
        marginal_improvement = -(cur.projected_high_risk_probability
                                 - prev.projected_high_risk_probability)
        if marginal_improvement < floor:
            return prev.intensity
    return None


def _interpretation(
    curve_points: List[DoseResponsePoint],
    sweet_spot: Optional[float],
    baseline: float,
) -> str:
    """Plain-English summary keyed off the shape of the curve."""
    if not curve_points:
        return "Could not compute a dose-response curve for this patient."

    best = min(curve_points, key=lambda p: p.projected_high_risk_probability)
    best_delta = best.delta_vs_baseline

    if best_delta >= 0:
        return (
            f"Across the swept doses none reduced projected high-risk "
            f"probability below the baseline of {baseline:.2f}. Consider a "
            f"different intervention type."
        )

    if sweet_spot is not None and sweet_spot < best.intensity:
        return (
            f"Most of the benefit shows up by intensity {sweet_spot:.1f} — "
            f"after that the curve flattens. The maximum benefit "
            f"(intensity {best.intensity:.1f}) lowers projected high-risk "
            f"probability by {abs(best_delta):.2f}, but the marginal gain "
            f"past {sweet_spot:.1f} is small enough that lower-effort "
            f"adherence may dominate the trade-off."
        )

    return (
        f"The curve continues to improve across the full swept range; the "
        f"lowest projected high-risk probability is {best.projected_high_risk_probability:.2f} "
        f"at intensity {best.intensity:.1f} (Δ {best_delta:.2f} from baseline)."
    )


def sweep_dose_response(req: DoseResponseRequest) -> DoseResponseCurve:
    grid = req.dose_grid or _DEFAULT_GRID
    grid = sorted({float(np.clip(d, 0.0, 1.0)) for d in grid})
    if not grid:
        raise ValueError("dose_grid must contain at least one intensity in [0, 1].")

    patient = req.patient_state
    horizon = min(req.horizon_days, 14)

    dyn, _stat = parse_patient_state(patient)
    static_features = patient.static_data.features
    starting_history = list(patient.dynamic_history)

    # Baseline reference.
    baseline_pred = RiskPredictionService().predict(
        dyn, np.array([static_features], dtype=np.float32),
    )
    baseline_high = float(baseline_pred["probabilities"][2])
    baseline_class = _RISK_LEVELS[int(baseline_pred["risk_class"])]

    # Sweep.
    points: List[DoseResponsePoint] = []
    prev_high: Optional[float] = None
    for intensity in grid:
        if intensity <= 0.0:
            # The "do-nothing" anchor.
            high = baseline_high
        else:
            projected = _project_horizon(
                dyn, int(req.intervention_type), float(intensity), horizon,
            )
            high = _horizon_end_high_risk(starting_history, projected, static_features)
        delta_baseline = high - baseline_high
        delta_prev = (high - prev_high) if prev_high is not None else None
        points.append(DoseResponsePoint(
            intensity=float(intensity),
            projected_high_risk_probability=high,
            delta_vs_baseline=delta_baseline,
            delta_vs_previous_dose=delta_prev,
        ))
        prev_high = high

    floor = 0.005
    sweet = _compute_sweet_spot(points, floor)

    return DoseResponseCurve(
        baseline_high_risk_probability=baseline_high,
        baseline_risk_class=baseline_class,
        horizon_days=horizon,
        intervention_type=req.intervention_type,
        points=points,
        sweet_spot_intensity=sweet,
        diminishing_returns_floor=floor,
        interpretation=_interpretation(points, sweet, baseline_high),
        source="live",
    )
