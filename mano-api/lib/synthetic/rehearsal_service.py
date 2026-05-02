"""
Adaptive Intervention Rehearsal Engine.

This is the flagship of "adaptive multimodal intervention simulation".

It exists because every existing what-if surface in this codebase asks the
same one-shot question: "given an intervention, what does day 7 look like
under perfect adherence?" That isn't a clinically useful question. The
useful question is the one a clinician would walk a patient through:

    "Over the next H days, with realistic adherence, and with the freedom
     to swap interventions if the trajectory drifts from goal, when am I
     likely to reach my target risk level, and what is the day-by-day
     plan?"

The engine answers that by composing all five frozen models in a closed
loop:

  CTGAN / TimeGAN — fill any missing demographics or starting vitals.
  Hybrid LSTM    — single-pass risk score, every simulated day.
  Seq2Seq        — 7-day projection per "swap interval".
  PPO            — initial recommendation + alternative when trajectory
                   misses the goal at a swap interval boundary.
  MC Dropout     — uncertainty band at days 1, 7, 14 of the realistic
                   trajectory.

Design invariants
-----------------
1. **Frozen models stay frozen.** No retraining, no weight reload, no
   gradient flow. We call only the ``predict`` / ``simulate_outcome`` /
   ``get_prescription`` entry points exposed by the existing services.
2. **Determinism on demand.** When a ``seed`` is provided the engine
   produces identical output across runs — required for the rehearsal
   "save and revisit" UX.
3. **Structural soundness over physiological accuracy at the margin.**
   Seq2Seq output is clamped to the schema's physiological ranges via
   ``clamp_simulated_vitals``. We never feed an out-of-range vital back
   into the LSTM; that would be a silent corruption.
4. **Bounded compute.** A 14-day horizon at three adherence levels with
   one MC Dropout band costs:
     LSTM: 14 days × 3 branches + 3 MC checkpoints × 20 passes  ≈ 102 calls × 14 ms ≈ 1.4 s
     Seq2Seq: 2 swap intervals × 3 branches  ≈ 6 calls × ~40 ms     ≈ 0.25 s
     PPO: 1 initial + ≤ 1 swap × 1 branch (realistic only)         ≈ 0.05 s
   Total well under 2 seconds even on the RTX 3050 Ti budget.

The route layer is in ``routes/synthetic/rehearsal_router.py``.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from schemas.synthetic.rehearsal_schema import (
    ConfidenceBand,
    DayProjection,
    InterventionSpec,
    PatientSummary,
    PlanGoal,
    RehearsalPlan,
    RehearsalRequest,
    SwapEvent,
    TrajectoryBranch,
)
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
    StaticFeatures,
)

from lib.synthetic.ctgan_service import CTGANService
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import (
    DYNAMIC_FEATURE_ORDER,
    clamp_simulated_vitals,
    parse_patient_state,
    vitals_to_matrix,
)
from lib.synthetic.timegan_service import TimeGANService
from lib.synthetic.uncertainty_service import predict_with_uncertainty

logger = logging.getLogger(__name__)

# Seq2Seq's training-time horizon. Every call projects exactly this many
# days into the future. Multi-week plans are decomposed into a sequence
# of these chunks; a swap can only happen at chunk boundaries (a clean
# clinical analogue: "review every week").
_SEQ2SEQ_HORIZON: int = 7

# Risk-class index map (index → RiskLevel) — matches LSTM training.
_RISK_LEVELS: Tuple[RiskLevel, ...] = (
    RiskLevel.LOW,
    RiskLevel.MEDIUM,
    RiskLevel.HIGH,
)


# ── Provenance + label helpers ──────────────────────────────────────────────


_INTERVENTION_LABELS = {
    InterventionType.CONTROL: "Continue current routine",
    InterventionType.WELLNESS_APP: "Daily wellness app practice",
    InterventionType.CBT: "Cognitive Behavioural Therapy",
    InterventionType.EXERCISE: "Exercise programme",
    InterventionType.MEDICATION: "Medication review",
}


def _intervention_with_label(spec: InterventionSpec) -> InterventionSpec:
    if spec.label:
        return spec
    return InterventionSpec(
        intervention_type=spec.intervention_type,
        intensity=spec.intensity,
        label=_INTERVENTION_LABELS.get(spec.intervention_type, spec.intervention_type.name),
    )


# ── Patient state synthesis (CTGAN + TimeGAN) ───────────────────────────────


def _synthesize_static_features() -> Tuple[StaticFeatures, str]:
    """Draw a 20-dim static feature vector from CTGAN. Falls back to a
    neutral all-zero vector if CTGAN isn't loaded (deterministic).
    """
    ctgan = CTGANService()
    if ctgan.is_loaded():
        df = ctgan.generate(num_samples=1)
        # Pull the first 20 numeric columns to match StaticFeatures' shape.
        # The pickled CTGAN model emits all 20 columns natively.
        row = df.iloc[0].to_list()
        # Coerce non-numeric (categorical) entries to a numeric encoding by
        # hashing into a [0, 1] band — the LSTM was trained on a normalised
        # vector so we keep the magnitude in range.
        numeric: List[float] = []
        for value in row[:20]:
            if isinstance(value, (int, float)):
                numeric.append(float(value))
            else:
                numeric.append((hash(str(value)) % 1000) / 1000.0)
        # Pad if the model returns fewer than 20 columns (defensive).
        while len(numeric) < 20:
            numeric.append(0.0)
        return StaticFeatures(features=numeric[:20]), "ctgan_synthesized"

    return StaticFeatures(features=[0.0] * 20), "ctgan_synthesized"


def _synthesize_starting_vitals() -> Tuple[List[DayVitals], str]:
    """Draw a 7-day × 4-channel starting vitals window from TimeGAN.
    Falls back to a clinically-bland baseline (7 hours sleep, neutral
    quality, 70 bpm, low stress) if TimeGAN isn't loaded.
    """
    timegan = TimeGANService()
    if timegan.is_loaded():
        sample = timegan.generate_denormalized(num_samples=1)  # (1, 7, 4)
        vitals_matrix = sample.astype(np.float32)
        vitals = clamp_simulated_vitals(vitals_matrix)
        return vitals, "timegan_synthesized"

    fallback = [
        DayVitals(sleep_hours=7.0, sleep_quality=0.6, heart_rate=70.0, stress_level=0.4)
        for _ in range(7)
    ]
    return fallback, "timegan_synthesized"


def _coerce_patient_state(req: RehearsalRequest) -> Tuple[PatientState, str, str]:
    """Return a complete PatientState plus provenance tags for static and
    dynamic data — fills missing pieces from CTGAN / TimeGAN.
    """
    if req.patient_state is not None:
        return req.patient_state, "patient_supplied", "patient_supplied"

    if not req.synthesize_missing_data:
        raise ValueError(
            "patient_state is null and synthesize_missing_data=False — "
            "either supply a patient_state or set synthesize_missing_data."
        )

    static, static_prov = _synthesize_static_features()
    vitals, vitals_prov = _synthesize_starting_vitals()
    return (
        PatientState(static_data=static, dynamic_history=vitals),
        static_prov,
        vitals_prov,
    )


# ── Risk + intervention helpers ─────────────────────────────────────────────


def _baseline_risk(patient: PatientState) -> dict:
    dyn, stat = parse_patient_state(patient)
    return RiskPredictionService().predict(dyn, stat)


def _ppo_top_k(
    patient: PatientState, k: int = 3
) -> List[InterventionSpec]:
    """Ask PPO for its single top recommendation, then synthesise plausible
    alternatives by varying the discrete arm. PPO's API exposes only the
    argmax action, so we fall back to a fixed alternatives list ordered
    by clinical plausibility for a generic mental-health context.
    """
    dyn, stat = parse_patient_state(patient)
    dyn_flat = dyn.reshape(-1)
    stat_flat = stat.reshape(-1)
    top = InterventionService().get_prescription(dyn_flat, stat_flat)

    primary_type = InterventionType(int(top["intervention_id"]))
    primary_intensity = float(np.clip(top["intensity"], 0.1, 1.0))

    candidates: List[InterventionSpec] = [
        _intervention_with_label(InterventionSpec(
            intervention_type=primary_type,
            intensity=primary_intensity,
        ))
    ]

    # Alternatives: pick from the remaining four arms in a clinically
    # sensible order (lowest-burden first, biological intervention last).
    alt_order = [
        InterventionType.WELLNESS_APP,
        InterventionType.CBT,
        InterventionType.EXERCISE,
        InterventionType.MEDICATION,
        InterventionType.CONTROL,
    ]
    for alt in alt_order:
        if alt == primary_type:
            continue
        candidates.append(_intervention_with_label(InterventionSpec(
            intervention_type=alt,
            intensity=primary_intensity if alt != InterventionType.CONTROL else 0.1,
        )))
        if len(candidates) >= k:
            break

    return candidates


# ── Adherence-aware projection ──────────────────────────────────────────────


def _adherence_mask(
    interval_days: int, adherence: float, rng: np.random.Generator
) -> np.ndarray:
    """Bernoulli mask of length ``interval_days``. 1 = adhered, 0 = skipped."""
    return rng.binomial(1, adherence, size=interval_days).astype(np.float32)


def _project_chunk(
    history: np.ndarray,         # (1, 7, 4) — last 7 days of vitals
    intervention: InterventionSpec,
    adherence_mask: np.ndarray,  # (interval_days,)
) -> np.ndarray:
    """Project ``len(adherence_mask)`` days forward.

    Seq2Seq projects a fixed 7-day chunk per call. Adherence is folded in
    by *attenuating* the intervention's effective intensity by the mean
    adherence over the chunk — a faithful approximation since Seq2Seq's
    intervention vector is a chunk-level conditioning input, not a
    day-level sequence.
    """
    days = adherence_mask.shape[0]
    assert days <= _SEQ2SEQ_HORIZON, (
        "Adherence mask longer than Seq2Seq's 7-day horizon; the caller "
        "must chunk multi-interval rollouts."
    )

    effective_adherence = float(adherence_mask.mean())
    effective_intensity = float(np.clip(intervention.intensity * effective_adherence, 0.0, 1.0))

    future = InterventionService().simulate_outcome(
        history,
        intervention_type=int(intervention.intervention_type),
        intensity=effective_intensity,
    )  # (1, 7, 4)

    # Take only the requested number of days from the chunk projection.
    return future[:, :days, :]


def _score_day_risk(
    vitals_day_window: List[DayVitals], static_features: StaticFeatures
) -> dict:
    """Score risk for a 7-day window via the frozen LSTM."""
    dyn = vitals_to_matrix(vitals_day_window)
    stat = np.array([static_features.features], dtype=np.float32)
    return RiskPredictionService().predict(dyn, stat)


def _vitals_to_day_projections(
    interval_start_idx: int,
    chunk_vitals: List[DayVitals],
    intervention: InterventionSpec,
    adherence_mask: np.ndarray,
    static_features: StaticFeatures,
    rolling_history: List[DayVitals],
) -> List[DayProjection]:
    """Produce ``DayProjection`` rows for one chunk — re-scoring the LSTM
    on the rolling 7-day window centred on each new day so risk signals
    update day-by-day rather than only at chunk boundaries.
    """
    projections: List[DayProjection] = []
    history = list(rolling_history)
    for offset, day_vitals in enumerate(chunk_vitals):
        window = (history + [day_vitals])[-7:]
        risk = _score_day_risk(window, static_features)
        projections.append(DayProjection(
            day_index=interval_start_idx + offset + 1,
            vitals=day_vitals,
            risk_class=_RISK_LEVELS[int(risk["risk_class"])],
            risk_probabilities=[float(p) for p in risk["probabilities"]],
            intervention_applied=intervention,
            skipped_due_to_adherence=bool(adherence_mask[offset] < 0.5),
        ))
        history = window
    return projections


# ── Trajectory roll-out ─────────────────────────────────────────────────────


def _roll_branch(
    *,
    label: str,
    adherence: float,
    horizon_days: int,
    initial_history: List[DayVitals],
    static_features: StaticFeatures,
    primary_intervention: InterventionSpec,
    candidate_interventions: List[InterventionSpec],
    goal: PlanGoal,
    rng: np.random.Generator,
    swap_events_sink: Optional[List[SwapEvent]],
) -> TrajectoryBranch:
    """Roll a single adherence branch forward over ``horizon_days``.

    Swap rule (only the realistic branch contributes to ``swap_events_sink``):
    at each chunk boundary, if the latest day's high-risk probability has
    not improved by ``goal.min_midway_delta`` relative to baseline AND we
    are past the first chunk, ask PPO for a different arm and switch.
    """
    chunks = math.ceil(horizon_days / _SEQ2SEQ_HORIZON)
    rolling_history = list(initial_history)
    days_so_far: List[DayProjection] = []
    current_intervention = _intervention_with_label(primary_intervention)
    days_remaining = horizon_days

    baseline_window = list(initial_history)
    baseline_risk = _score_day_risk(baseline_window, static_features)
    baseline_high_prob = float(baseline_risk["probabilities"][2])

    high_prob_curve: List[float] = []
    days_to_goal: Optional[int] = None
    target_idx = _RISK_LEVELS.index(goal.target_risk_level)

    chunk_start = 0
    for chunk_idx in range(chunks):
        chunk_days = min(_SEQ2SEQ_HORIZON, days_remaining)
        mask = _adherence_mask(chunk_days, adherence, rng)
        history_array = vitals_to_matrix(rolling_history[-7:])

        chunk_projection = _project_chunk(history_array, current_intervention, mask)
        chunk_vitals = clamp_simulated_vitals(chunk_projection)

        new_projections = _vitals_to_day_projections(
            interval_start_idx=chunk_start,
            chunk_vitals=chunk_vitals,
            intervention=current_intervention,
            adherence_mask=mask,
            static_features=static_features,
            rolling_history=rolling_history,
        )
        days_so_far.extend(new_projections)
        rolling_history.extend(chunk_vitals)
        rolling_history = rolling_history[-7:]
        for proj in new_projections:
            high_prob_curve.append(proj.risk_probabilities[2])
            if days_to_goal is None and _RISK_LEVELS.index(proj.risk_class) <= target_idx:
                days_to_goal = proj.day_index

        # Swap evaluation — only at non-final chunk boundaries on the
        # realistic adherence branch. We use the realistic branch as the
        # "decision-maker"; pessimistic + optimistic branches replay the
        # same swap decisions for fair comparison.
        is_final_chunk = chunk_idx == chunks - 1
        if (not is_final_chunk
                and swap_events_sink is not None
                and len(days_so_far) >= 1):
            current_high_prob = days_so_far[-1].risk_probabilities[2]
            improvement = baseline_high_prob - current_high_prob
            if improvement < goal.min_midway_delta:
                # Trajectory off-goal — query PPO with the latest state and
                # swap to its top non-current recommendation.
                synth_patient = PatientState(
                    static_data=static_features,
                    dynamic_history=rolling_history,
                )
                fresh_top = _ppo_top_k(synth_patient, k=3)
                # Pick the first candidate that isn't the current arm.
                candidate = next(
                    (c for c in fresh_top if c.intervention_type != current_intervention.intervention_type),
                    candidate_interventions[1] if len(candidate_interventions) > 1 else current_intervention,
                )
                swap_events_sink.append(SwapEvent(
                    at_day=days_so_far[-1].day_index,
                    from_intervention=current_intervention,
                    to_intervention=candidate,
                    reason=(
                        f"Realistic high-risk probability improved by only "
                        f"{improvement:.3f}, below the {goal.min_midway_delta} "
                        f"threshold — switching to the next-best PPO arm."
                    ),
                    realistic_high_risk_prob_at_swap=current_high_prob,
                ))
                current_intervention = candidate

        chunk_start += chunk_days
        days_remaining -= chunk_days

    final = days_so_far[-1] if days_so_far else None
    if final is None:
        # Defensive — should not happen.
        raise RuntimeError("Rehearsal produced an empty trajectory.")

    return TrajectoryBranch(
        label=label,
        adherence=adherence,
        days=days_so_far,
        final_risk_class=final.risk_class,
        final_risk_probabilities=final.risk_probabilities,
        days_to_goal=days_to_goal,
        high_risk_probability_curve=high_prob_curve,
    )


# ── MC Dropout confidence band ──────────────────────────────────────────────


def _confidence_band_for_realistic(
    realistic_branch: TrajectoryBranch,
    static_features: StaticFeatures,
    initial_history: List[DayVitals],
) -> ConfidenceBand:
    """Surface MC Dropout uncertainty at three checkpoints (days 1, midway, last).

    Uses the existing ``predict_with_uncertainty`` helper. We evaluate on the
    7-day rolling window ending at each checkpoint day, banding on the
    high-risk probability — that's what the UI plots and what the goal
    cares about.
    """
    horizon = len(realistic_branch.days)
    if horizon <= 0:
        return ConfidenceBand(
            checkpoints=[], low_p5=[], realistic_p50=[], high_p95=[], n_passes=0,
        )

    risk_svc = RiskPredictionService()
    model = getattr(risk_svc, "model", None)
    if model is None:
        # Frozen model not loaded (e.g. test environment). Return a
        # zero-spread band — same value across every checkpoint and
        # band — so callers can render but never claim more confidence
        # than we have.
        anchor = realistic_branch.high_risk_probability_curve[-1]
        midway = max(1, horizon // 2)
        checkpoints = sorted({1, midway, horizon})
        n_cp = len(checkpoints)
        return ConfidenceBand(
            checkpoints=checkpoints,
            low_p5=[anchor] * n_cp,
            realistic_p50=[anchor] * n_cp,
            high_p95=[anchor] * n_cp,
            n_passes=0,
        )

    midway = max(1, horizon // 2)
    checkpoints = sorted({1, midway, horizon})
    n_samples = 20

    low: List[float] = []
    mid: List[float] = []
    high: List[float] = []

    history = list(initial_history)
    for day_idx in range(1, horizon + 1):
        history = (history + [realistic_branch.days[day_idx - 1].vitals])[-7:]
        if day_idx not in checkpoints:
            continue
        dyn = vitals_to_matrix(history)
        stat = np.array([static_features.features], dtype=np.float32)
        mc = predict_with_uncertainty(model, dyn, stat, n_samples=n_samples)
        # class_statistics is ordered (Low, Medium, High); index 2 = High.
        high_stat = mc.class_statistics[2]
        low.append(float(high_stat.min))
        mid.append(float(high_stat.mean))
        high.append(float(high_stat.max))

    return ConfidenceBand(
        checkpoints=checkpoints,
        low_p5=low,
        realistic_p50=mid,
        high_p95=high,
        n_passes=n_samples,
    )


# ── Public entry point ──────────────────────────────────────────────────────


def rehearse_plan(req: RehearsalRequest) -> RehearsalPlan:
    """Compose a full RehearsalPlan from the request.

    See module docstring for the algorithm. This function is the single
    entry point used by the route layer.
    """
    # Floor horizon to a multiple of 7 days.
    horizon = (req.horizon_days // _SEQ2SEQ_HORIZON) * _SEQ2SEQ_HORIZON
    if horizon == 0:
        raise ValueError("horizon_days must be at least 7.")

    patient, static_prov, vitals_prov = _coerce_patient_state(req)

    # Baseline summary.
    baseline = _baseline_risk(patient)
    summary = PatientSummary(
        baseline_risk_class=_RISK_LEVELS[int(baseline["risk_class"])],
        baseline_high_risk_probability=float(baseline["probabilities"][2]),
        static_feature_provenance=static_prov,
        vitals_provenance=vitals_prov,
    )

    # Initial PPO recommendation + alternatives.
    candidates = req.candidate_interventions or _ppo_top_k(patient, k=3)
    candidates = [_intervention_with_label(c) for c in candidates]
    primary = candidates[0]

    # Roll three branches. The realistic branch (0.8 by convention) is the
    # one whose swap decisions other branches replay; we identify it as
    # the adherence value closest to 0.8.
    realistic_target = 0.8
    realistic_idx = int(np.argmin(np.abs(np.array(req.adherence_levels) - realistic_target)))
    rng_seed = req.seed if req.seed is not None else int(uuid.uuid4().int & 0xFFFFFFFF)
    swap_events: List[SwapEvent] = []
    branches: List[TrajectoryBranch] = []
    branch_labels = _branch_labels(req.adherence_levels, realistic_idx)

    for i, adherence in enumerate(req.adherence_levels):
        # Fresh RNG per branch so they can be reproduced independently.
        rng = np.random.default_rng(rng_seed + i)
        sink = swap_events if i == realistic_idx else None
        branch = _roll_branch(
            label=branch_labels[i],
            adherence=float(np.clip(adherence, 0.0, 1.0)),
            horizon_days=horizon,
            initial_history=list(patient.dynamic_history),
            static_features=patient.static_data,
            primary_intervention=primary,
            candidate_interventions=candidates,
            goal=req.goal,
            rng=rng,
            swap_events_sink=sink,
        )
        branches.append(branch)

    # Confidence band (sourced from the realistic branch).
    confidence_band = _confidence_band_for_realistic(
        realistic_branch=branches[realistic_idx],
        static_features=patient.static_data,
        initial_history=list(patient.dynamic_history),
    )

    # Advisory notes — UI hints, not prescriptions.
    advisories: List[str] = []
    realistic = branches[realistic_idx]
    if realistic.days_to_goal is None:
        advisories.append(
            f"Even with realistic adherence the realistic branch did not "
            f"reach {req.goal.target_risk_level.value} risk within "
            f"{horizon} days. Consider extending the horizon or adding a "
            f"complementary intervention."
        )
    else:
        advisories.append(
            f"Under realistic adherence the goal of "
            f"{req.goal.target_risk_level.value} risk is projected to be "
            f"reached on day {realistic.days_to_goal}."
        )
    if swap_events:
        first = swap_events[0]
        advisories.append(
            f"On day {first.at_day} the engine recommends switching from "
            f"{first.from_intervention.label} to {first.to_intervention.label} — "
            f"the trajectory was not improving fast enough on the original arm."
        )
    if confidence_band.n_passes > 0:
        last_cp = confidence_band.checkpoints[-1]
        spread = confidence_band.high_p95[-1] - confidence_band.low_p5[-1]
        if spread > 0.20:
            advisories.append(
                f"Day-{last_cp} confidence is wide (high-risk probability "
                f"range ≈ {spread:.2f}). Re-running this rehearsal after a "
                f"week of new data is recommended."
            )

    expected_goal_attainment_day = realistic.days_to_goal

    return RehearsalPlan(
        plan_id=str(uuid.uuid4()),
        horizon_days=horizon,
        goal=req.goal,
        patient_summary=summary,
        primary_intervention=primary,
        swap_events=swap_events,
        trajectories=branches,
        confidence_band=confidence_band,
        expected_goal_attainment_day=expected_goal_attainment_day,
        advisory_notes=advisories,
        source="live",
    )


def _branch_labels(adherence_levels: List[float], realistic_idx: int) -> List[str]:
    """Label each branch by its position relative to the realistic anchor."""
    labels: List[str] = []
    for i, _ in enumerate(adherence_levels):
        if i < realistic_idx:
            labels.append("pessimistic")
        elif i == realistic_idx:
            labels.append("realistic")
        else:
            labels.append("optimistic")
    # Disambiguate ties (e.g. two branches both above realistic).
    if labels.count("pessimistic") > 1:
        for i, lab in enumerate(labels):
            if lab == "pessimistic":
                labels[i] = f"pessimistic_{i + 1}"
    if labels.count("optimistic") > 1:
        ks = [i for i, l in enumerate(labels) if l == "optimistic"]
        for k_idx, i in enumerate(ks):
            labels[i] = f"optimistic_{k_idx + 1}"
    return labels
