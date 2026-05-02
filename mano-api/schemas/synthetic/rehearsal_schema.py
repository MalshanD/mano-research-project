"""
Pydantic schemas for the Adaptive Intervention Rehearsal Engine.

The rehearsal engine answers a fundamentally different question from the
existing one-shot what-if endpoints. Instead of:

    "If I prescribe CBT at intensity 0.5, what does day 7 look like?"

it answers:

    "Over the next 14 days, with realistic 80 % adherence and the freedom
     to swap to a different intervention if the trajectory drifts off
     goal, when am I likely to reach Low risk, and what is the day-by-day
     plan?"

The shape of this answer involves three branches (pessimistic / realistic /
optimistic adherence), the swap log, the daily projected vitals + risk,
and a confidence band sourced from MC Dropout on the realistic branch.

All math sits in ``lib/synthetic/rehearsal_service.py``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
)


# ── Inputs ──────────────────────────────────────────────────────────────────


class InterventionSpec(BaseModel):
    """One concrete intervention the engine can prescribe / swap to."""

    intervention_type: InterventionType
    intensity: float = Field(
        0.5,
        ge=0.1, le=1.0,
        description="Base intensity (0.1–1.0). Effective intensity is "
                    "scaled by adherence at simulation time.",
    )
    label: Optional[str] = Field(
        None,
        description="Human-readable label for the rehearsal UI. Auto-derived "
                    "from intervention_type if omitted.",
    )


class PlanGoal(BaseModel):
    """The patient's outcome goal that the engine plans against.

    The goal drives the swap rule: if the realistic trajectory's projected
    end-state risk class is worse than ``target_risk_level`` AND the
    midway projection has not improved by ``min_midway_delta`` from the
    baseline, the engine queries PPO for a different intervention.
    """

    target_risk_level: RiskLevel = Field(
        RiskLevel.LOW,
        description="The risk level the patient is aiming to reach.",
    )
    target_window_days: int = Field(
        14,
        ge=3, le=90,
        description="By when (days) the patient hopes to reach the target.",
    )
    min_midway_delta: float = Field(
        0.05,
        ge=0.0, le=1.0,
        description="Minimum reduction in High-risk probability we need to "
                    "see by the mid-plan checkpoint to consider the plan "
                    "on-track. Below this, the engine swaps interventions.",
    )


class RehearsalRequest(BaseModel):
    """Top-level request. Either supply a full ``patient_state`` or rely
    on ``synthesize_missing_data=True`` to draw a fresh patient from
    CTGAN + TimeGAN — useful for demos and worked examples.
    """

    patient_state: Optional[PatientState] = None
    synthesize_missing_data: bool = Field(
        False,
        description="When True and patient_state is null, the engine draws "
                    "one synthetic patient from CTGAN + TimeGAN.",
    )

    goal: PlanGoal = Field(default_factory=PlanGoal)
    horizon_days: int = Field(
        14,
        ge=7, le=28,
        description="Total plan length. Must be a multiple of 7 since "
                    "Seq2Seq's natural projection horizon is 7 days; "
                    "values are floored to the nearest multiple of 7.",
    )

    candidate_interventions: Optional[List[InterventionSpec]] = Field(
        None,
        description="The interventions the engine may swap among. Defaults "
                    "to the PPO top-3 plus the literal Control arm.",
    )
    adherence_levels: List[float] = Field(
        default_factory=lambda: [0.6, 0.8, 0.95],
        description="The three adherence rates to bracket pessimistic / "
                    "realistic / optimistic outcomes.",
    )
    seed: Optional[int] = Field(
        None,
        description="Optional seed for the adherence bernoulli draws — "
                    "fixes reproducibility for a given (patient, plan) pair.",
    )


# ── Outputs ─────────────────────────────────────────────────────────────────


class DayProjection(BaseModel):
    """One day in a rehearsed trajectory."""

    day_index: int = Field(..., ge=1, description="1-indexed day in the plan.")
    vitals: DayVitals
    risk_class: RiskLevel
    risk_probabilities: List[float] = Field(
        ..., min_length=3, max_length=3,
        description="[Low, Medium, High] probabilities from the LSTM.",
    )
    intervention_applied: InterventionSpec
    skipped_due_to_adherence: bool = Field(
        False,
        description="True when the adherence draw said 'no' for this day; "
                    "intensity is dropped to the Control level for the "
                    "Seq2Seq projection on this day.",
    )


class TrajectoryBranch(BaseModel):
    """One adherence branch of the rehearsed plan."""

    label: str = Field(
        ...,
        description="'pessimistic' | 'realistic' | 'optimistic'",
    )
    adherence: float
    days: List[DayProjection]
    final_risk_class: RiskLevel
    final_risk_probabilities: List[float]
    days_to_goal: Optional[int] = Field(
        None,
        description="Day index at which the projected risk first reached "
                    "the goal level. None if the goal is not attained "
                    "within the horizon.",
    )
    high_risk_probability_curve: List[float] = Field(
        ...,
        description="Day-by-day high-risk probability — convenient for "
                    "rendering the band chart on the frontend.",
    )


class SwapEvent(BaseModel):
    """An audit-trail entry recording when the engine swapped interventions."""

    at_day: int = Field(..., ge=1)
    from_intervention: InterventionSpec
    to_intervention: InterventionSpec
    reason: str
    realistic_high_risk_prob_at_swap: float


class ConfidenceBand(BaseModel):
    """MC-Dropout-derived confidence intervals at key checkpoints."""

    checkpoints: List[int] = Field(
        ...,
        description="Day indices at which MC Dropout was run.",
    )
    low_p5: List[float]
    realistic_p50: List[float]
    high_p95: List[float]
    n_passes: int


class PatientSummary(BaseModel):
    """Compact baseline summary surfaced in the response."""

    baseline_risk_class: RiskLevel
    baseline_high_risk_probability: float
    static_feature_provenance: str = Field(
        ...,
        description="'patient_supplied' | 'ctgan_synthesized'",
    )
    vitals_provenance: str = Field(
        ...,
        description="'patient_supplied' | 'timegan_synthesized'",
    )


class RehearsalPlan(BaseModel):
    """The full rehearsed plan returned to the caller."""

    plan_id: str
    horizon_days: int
    goal: PlanGoal
    patient_summary: PatientSummary

    primary_intervention: InterventionSpec
    swap_events: List[SwapEvent] = Field(default_factory=list)

    trajectories: List[TrajectoryBranch] = Field(
        ..., min_length=1, max_length=5,
        description="One branch per adherence level requested.",
    )
    confidence_band: ConfidenceBand

    expected_goal_attainment_day: Optional[int] = Field(
        None,
        description="The day the realistic trajectory first reaches the "
                    "goal. None if the goal is not attained within horizon.",
    )

    advisory_notes: List[str] = Field(
        default_factory=list,
        description="Plain-English advisory bullets for the frontend to "
                    "render alongside the chart (e.g. 'low confidence on "
                    "day 14 — consider re-checking after a week').",
    )

    source: str = Field(
        "live",
        description="Provenance tag — always 'live' here, but kept for "
                    "consistency with other C1 enhancement endpoints.",
    )
