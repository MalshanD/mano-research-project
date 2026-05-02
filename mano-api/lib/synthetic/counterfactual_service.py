"""
Intervention counterfactual reasoning.

Clinical question
-----------------
Given a patient's current 7-day history, if the clinician applies
*intervention A* (factual) vs *intervention B* (counterfactual) over the next
N days, how do the two trajectories differ — in vitals, in per-day risk
class, and in aggregate high-risk probability?

Implementation
--------------
We reuse the recursive-rollout machinery from ``trajectory_service`` for each
arm. The two arms use identical input history and static features — the
only varying factor is the (intervention_type, intensity) pair. This isolates
the *intervention's* causal contribution under the frozen Seq2Seq's learned
dynamics.

Metrics
-------
* ``risk_reduction_score`` — mean(high_risk_prob | factual) -
  mean(high_risk_prob | counterfactual). Positive means the counterfactual
  arm reduces average high-risk probability across the horizon.
* ``risk_reduction_per_day`` — same delta computed per day; useful for the
  UI to chart when the two arms diverge.
* ``vitals_divergence`` — mean absolute difference per vitals feature over
  the horizon. Surfaces *which* physiological axis the intervention moves.
* ``dominant_feature`` — the argmax of ``vitals_divergence``.

Caveats
-------
* The frozen Seq2Seq never saw RCT-style counterfactual pairs during
  training; it learned conditional dynamics from observational synthetic
  data. These outputs are therefore *model-based* counterfactuals, not
  identified causal effects. We label them as such in the interpretation
  string so downstream consumers don't over-interpret them.
* Past day 7 the same compounding-error caveat from ``trajectory_service``
  applies — we re-surface it in ``notes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np

from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import DYNAMIC_FEATURE_ORDER, vitals_to_matrix
from lib.synthetic.trajectory_service import forecast_trajectory
from schemas.synthetic.simulation_schema import DayVitals, InterventionType, RiskLevel

logger = logging.getLogger(__name__)


_INTERVENTION_NAMES: Dict[int, str] = {
    InterventionType.CONTROL.value: "Control",
    InterventionType.WELLNESS_APP.value: "Wellness App",
    InterventionType.CBT.value: "CBT",
    InterventionType.EXERCISE.value: "Exercise",
    InterventionType.MEDICATION.value: "Medication",
}


def _outcome_from_trajectory(
    *,
    arm_result: Dict[str, Any],
    intervention_type: InterventionType,
    intensity: float,
) -> Dict[str, Any]:
    """Adapt a trajectory-service dict into a flatter 'InterventionOutcome' dict.

    We don't construct Pydantic models here — the route layer does that.
    This keeps the service pure (pure Python types) and easy to unit-test.
    """
    forecasts: List[Dict[str, Any]] = arm_result["forecasts"]
    vitals: List[DayVitals] = [f["vitals"] for f in forecasts]

    high_risk_series = [f["risk_probabilities"][2] for f in forecasts]
    mean_high_risk = float(np.mean(high_risk_series)) if high_risk_series else 0.0

    last_day = forecasts[-1] if forecasts else None

    return {
        "intervention_name": _INTERVENTION_NAMES.get(intervention_type.value, str(intervention_type.name)),
        "intervention_type": intervention_type,
        "intensity": float(intensity),
        "horizon_days": arm_result["horizon_days"],
        "forecast_vitals": vitals,
        "risk_trajectory": [
            {
                "day_index": f["day_index"],
                "risk_class": f["risk_class"],
                "risk_confidence": f["risk_confidence"],
                "risk_probabilities": f["risk_probabilities"],
                "predictive_entropy": f.get("predictive_entropy"),
            }
            for f in forecasts
        ],
        "final_risk_class": last_day["risk_class"] if last_day else RiskLevel.LOW,
        "final_risk_probabilities": last_day["risk_probabilities"] if last_day else [1.0, 0.0, 0.0],
        "mean_high_risk_probability": round(mean_high_risk, 4),
        "trajectory_shape": arm_result["trajectory_shape"],
    }


def _vitals_divergence(
    factual_vitals: List[DayVitals],
    counterfactual_vitals: List[DayVitals],
) -> Tuple[Dict[str, float], str]:
    """Mean absolute per-feature divergence between the two arms."""
    f_mat = vitals_to_matrix(factual_vitals)[0]   # (T, 4)
    c_mat = vitals_to_matrix(counterfactual_vitals)[0]

    # Align to the shorter horizon in case rollouts differ in length.
    n = min(f_mat.shape[0], c_mat.shape[0])
    diff = np.abs(f_mat[:n] - c_mat[:n]).mean(axis=0)

    divergence = {
        name: round(float(val), 4)
        for name, val in zip(DYNAMIC_FEATURE_ORDER, diff)
    }
    if not divergence:
        return {}, ""
    dominant = max(divergence, key=divergence.get)
    return divergence, dominant


def _interpretation(
    *,
    factual_name: str,
    counterfactual_name: str,
    risk_reduction_score: float,
    dominant_feature: str,
) -> str:
    """Plain-language summary for the UI."""
    if abs(risk_reduction_score) < 0.02:
        return (
            f"Modeled effect size between {factual_name} and {counterfactual_name} "
            f"is negligible (<2% high-risk probability)."
        )

    better = counterfactual_name if risk_reduction_score > 0 else factual_name
    delta_pp = abs(risk_reduction_score) * 100
    return (
        f"Model-based counterfactual: {better} lowers mean high-risk probability "
        f"by {delta_pp:.1f} percentage points across the horizon. Largest "
        f"physiological divergence is on {dominant_feature}. "
        f"This is a model-based estimate, not an identified causal effect."
    )


def run_counterfactual(
    *,
    dynamic_np: np.ndarray,
    static_np: np.ndarray,
    factual_intervention: InterventionType,
    factual_intensity: float,
    counterfactual_intervention: InterventionType,
    counterfactual_intensity: float,
    horizon_days: int,
    uncertainty_samples: int,
    intervention_service: InterventionService,
    risk_service: RiskPredictionService,
) -> Dict[str, Any]:
    """Roll both arms forward and compute comparison metrics.

    The two arms are simulated independently with identical initial state.
    We return a dict ready for the route to wrap in Pydantic response models.
    """
    if factual_intervention == counterfactual_intervention and abs(
        factual_intensity - counterfactual_intensity
    ) < 1e-6:
        logger.info(
            "counterfactual_identical_arms",
            extra={"intervention": factual_intervention.name},
        )

    # ── Arm 1: factual ─────────────────────────────────────────────────────
    factual_result = forecast_trajectory(
        dynamic_np=dynamic_np,
        static_np=static_np,
        intervention_type=int(factual_intervention.value),
        intensity=float(factual_intensity),
        horizon_days=horizon_days,
        uncertainty_samples=uncertainty_samples,
        intervention_service=intervention_service,
        risk_service=risk_service,
    )

    # ── Arm 2: counterfactual ──────────────────────────────────────────────
    counterfactual_result = forecast_trajectory(
        dynamic_np=dynamic_np,
        static_np=static_np,
        intervention_type=int(counterfactual_intervention.value),
        intensity=float(counterfactual_intensity),
        horizon_days=horizon_days,
        uncertainty_samples=uncertainty_samples,
        intervention_service=intervention_service,
        risk_service=risk_service,
    )

    factual_outcome = _outcome_from_trajectory(
        arm_result=factual_result,
        intervention_type=factual_intervention,
        intensity=factual_intensity,
    )
    counterfactual_outcome = _outcome_from_trajectory(
        arm_result=counterfactual_result,
        intervention_type=counterfactual_intervention,
        intensity=counterfactual_intensity,
    )

    # ── Effect-size metrics ────────────────────────────────────────────────
    f_high = [f["risk_probabilities"][2] for f in factual_result["forecasts"]]
    c_high = [f["risk_probabilities"][2] for f in counterfactual_result["forecasts"]]
    n = min(len(f_high), len(c_high))
    per_day = [round(float(f_high[i] - c_high[i]), 4) for i in range(n)]
    score = round(
        float(factual_outcome["mean_high_risk_probability"])
        - float(counterfactual_outcome["mean_high_risk_probability"]),
        4,
    )
    cf_better = score > 0

    # ── Mechanism: where do the two arms diverge physiologically? ──────────
    divergence, dominant = _vitals_divergence(
        factual_outcome["forecast_vitals"],
        counterfactual_outcome["forecast_vitals"],
    )

    interpretation = _interpretation(
        factual_name=factual_outcome["intervention_name"],
        counterfactual_name=counterfactual_outcome["intervention_name"],
        risk_reduction_score=score,
        dominant_feature=dominant or "overall vitals",
    )

    # Combine notes from both arms, dedupe while preserving order.
    merged_notes: List[str] = []
    for note in (factual_result.get("notes", []) + counterfactual_result.get("notes", [])):
        if note not in merged_notes:
            merged_notes.append(note)

    return {
        "factual": factual_outcome,
        "counterfactual": counterfactual_outcome,
        "risk_reduction_score": score,
        "risk_reduction_per_day": per_day,
        "counterfactual_is_better": cf_better,
        "vitals_divergence": divergence,
        "dominant_feature": dominant or None,
        "interpretation": interpretation,
        "notes": merged_notes,
    }
