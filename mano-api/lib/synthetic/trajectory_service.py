"""
Multi-horizon trajectory forecasting.

Goal
----
The frozen Seq2Seq simulator natively emits a 7-day forecast. For the
Future-Self narrative, the clinical passport, and the dashboard trend cards,
we frequently need 14- or 21-day trajectories with uncertainty bands.

Approach
--------
We *recursively* roll the simulator forward one 7-day window at a time:

    window_1 = simulator(input_vitals_7d, intervention, intensity)
    window_2 = simulator(window_1,        intervention, intensity)
    ...

At each simulated day we feed the vitals into the frozen Hybrid LSTM risk
classifier. When the caller asks for uncertainty bands, we additionally run
N MC-Dropout forward passes per day via ``uncertainty_service``.

Why this is a *phantom-day extrapolation*, not a retrained long-horizon model
----------------------------------------------------------------------------
The user's requirement is explicit: the five core models are FROZEN. Retraining
a longer-horizon seq-to-seq is not on the table. Recursive rollout is the
standard workaround and is a well-understood technique in clinical simulation
literature. It introduces compounding error, which we mitigate by:

* Clamping every intermediate window's vitals to their physical ranges
  (prevents runaway drift when the simulator over-shoots).
* Surfacing the uncertainty band explicitly so consumers can fade confidence
  visually as the horizon grows.
* Labeling the ``trajectory_shape`` with a qualitative heuristic so the UI
  can avoid implying false precision at day 14+.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import clamp_simulated_vitals, vitals_to_matrix
from lib.synthetic.uncertainty_service import predict_with_uncertainty
from schemas.synthetic.simulation_schema import DayVitals, RiskLevel

logger = logging.getLogger(__name__)

# Each Seq2Seq window is always 7 days — a property of the frozen checkpoint.
_WINDOW_DAYS = 7

# Risk-class lookups. Matches the ordering used by the frozen LSTM head.
_RISK_LEVEL = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}
_CLASS_NAMES = ("Low", "Medium", "High")


def _classify_trajectory_shape(risk_classes: List[int]) -> str:
    """Summarise a list of per-day integer risk classes.

    Heuristic — we look at the average slope of the risk-class series and the
    variance around that slope. No magic; just enough to label the trend for
    the UI so we don't mislead the user with a numeric risk that over-varies.
    """
    if len(risk_classes) < 2:
        return "stable"

    n = len(risk_classes)
    xs = np.arange(n, dtype=np.float64)
    ys = np.asarray(risk_classes, dtype=np.float64)

    # linear fit: y = slope * x + intercept
    slope = float(np.polyfit(xs, ys, deg=1)[0])
    residuals = ys - (slope * xs + (ys.mean() - slope * xs.mean()))
    residual_std = float(residuals.std())

    if residual_std > 0.6 and abs(slope) < 0.05:
        return "oscillating"
    if slope < -0.05:
        return "improving"
    if slope > 0.05:
        return "worsening"
    return "stable"


def _build_intervention_vector(
    intervention_type: int, intensity: float, device: torch.device | str,
) -> torch.Tensor:
    """Construct the (1, 6) one-hot-plus-intensity vector the Seq2Seq expects."""
    vec = torch.zeros(1, 6, device=device)
    vec[0, intervention_type] = 1.0
    vec[0, 5] = float(intensity)
    return vec


def _simulate_window(
    intervention_service: InterventionService,
    dynamic_np: np.ndarray,
    intervention_type: int,
    intensity: float,
) -> np.ndarray:
    """Run the Seq2Seq for one 7-day window. Returns shape (1, 7, 4)."""
    if intervention_service.simulator is None:
        raise RuntimeError("Intervention simulator is not loaded")

    device = intervention_service.device or "cpu"
    intervention_vec = _build_intervention_vector(intervention_type, intensity, device)
    patient_tensor = torch.as_tensor(dynamic_np, dtype=torch.float32, device=device)

    with torch.no_grad():
        future = intervention_service.simulator(
            patient_tensor,
            intervention_vec,
            target=None,
            teacher_forcing_ratio=0.0,
        )
    return future.cpu().numpy()


def forecast_trajectory(
    *,
    dynamic_np: np.ndarray,
    static_np: np.ndarray,
    intervention_type: int,
    intensity: float,
    horizon_days: int,
    uncertainty_samples: int,
    intervention_service: InterventionService,
    risk_service: RiskPredictionService,
) -> Dict[str, Any]:
    """Forecast a multi-day trajectory with per-day risk + optional uncertainty.

    Inputs are numpy arrays produced by ``parse_patient_state``. Returns a
    dict shaped for direct consumption by the route handler — the route
    adapts it into the Pydantic response.
    """
    if risk_service.model is None:
        raise RuntimeError("Risk model is not loaded")
    if horizon_days < _WINDOW_DAYS:
        raise ValueError(f"horizon_days must be >= {_WINDOW_DAYS}")

    num_windows = math.ceil(horizon_days / _WINDOW_DAYS)
    current_window = dynamic_np  # (1, 7, 4) — always the trailing 7 days.
    all_day_vitals: List[DayVitals] = []

    # ── Step 1: roll the simulator forward one window at a time ────────────
    for window_idx in range(num_windows):
        future_window = _simulate_window(
            intervention_service=intervention_service,
            dynamic_np=current_window,
            intervention_type=intervention_type,
            intensity=intensity,
        )
        # Clamp to schema-valid ranges before the LSTM sees them. This is the
        # same clamp used at the simulation_router endpoint.
        window_vitals = clamp_simulated_vitals(future_window)
        all_day_vitals.extend(window_vitals)

        # Prepare the next window's input. We shift so the next simulation
        # starts from this window's output — standard recursive rollout.
        current_window = vitals_to_matrix(window_vitals)

    # Trim to the exact horizon the caller requested.
    all_day_vitals = all_day_vitals[:horizon_days]

    # ── Step 2: per-day risk + optional uncertainty sweep ─────────────────
    forecasts: List[Dict[str, Any]] = []
    risk_classes: List[int] = []
    peak_risk_day: Optional[int] = None
    peak_risk_class = -1

    # The LSTM expects a 7-day window. For each forecast day we assemble the
    # rolling 7-day history ending at that day; days 1..6 borrow the tail of
    # the input window plus newly-simulated days.
    rolling_history = np.concatenate([dynamic_np[0], vitals_to_matrix(all_day_vitals)[0]], axis=0)
    # rolling_history shape: (7 + horizon_days, 4)

    for day_idx, vitals in enumerate(all_day_vitals):
        # 7-day window ending at this forecast day (inclusive)
        end = 7 + day_idx + 1  # +1 because slicing end is exclusive
        window_np = rolling_history[end - 7:end][np.newaxis, :, :].astype(np.float32)

        point_risk = risk_service.predict(window_np, static_np)
        day_info: Dict[str, Any] = {
            "day_index": day_idx + 1,
            "vitals": vitals,
            "risk_class": _RISK_LEVEL[point_risk["risk_class"]],
            "risk_confidence": round(float(point_risk["confidence"]), 4),
            "risk_probabilities": [round(float(p), 4) for p in point_risk["probabilities"]],
            "risk_probability_std": None,
            "predictive_entropy": None,
            "mutual_information": None,
        }

        if uncertainty_samples > 0:
            try:
                u = predict_with_uncertainty(
                    model=risk_service.model,
                    dynamic_np=window_np,
                    static_np=static_np,
                    device=risk_service.device,
                    n_samples=uncertainty_samples,
                    class_names=_CLASS_NAMES,
                    point_probabilities=point_risk["probabilities"],
                    point_class=point_risk["risk_class"],
                )
                day_info["risk_probability_std"] = [cs.std for cs in u.class_statistics]
                day_info["predictive_entropy"] = u.predictive_entropy
                day_info["mutual_information"] = u.mutual_information
            except Exception as exc:  # pragma: no cover — model failure path
                logger.warning("trajectory_uncertainty_failed", extra={"day": day_idx + 1, "error": str(exc)})

        risk_classes.append(point_risk["risk_class"])
        if point_risk["risk_class"] > peak_risk_class:
            peak_risk_class = point_risk["risk_class"]
            peak_risk_day = day_idx + 1

        forecasts.append(day_info)

    shape = _classify_trajectory_shape(risk_classes)

    notes: List[str] = []
    # Surface compounding-error caveat explicitly past day 7 — this keeps the
    # UI honest about the recursive-rollout limitation.
    if horizon_days > _WINDOW_DAYS:
        notes.append(
            "Days beyond 7 are extrapolated recursively. Confidence decreases "
            "with horizon; prefer the uncertainty band over the point class."
        )

    return {
        "horizon_days": horizon_days,
        "forecasts": forecasts,
        "peak_risk_day": peak_risk_day,
        "peak_risk_class": _RISK_LEVEL.get(peak_risk_class) if peak_risk_class >= 0 else None,
        "trajectory_shape": shape,
        "notes": notes,
    }
