"""
Care-Path Therapy Orchestrator.

A longitudinal state machine that sits above the conversational chat state
machine in ``lib/therapy/therapy_service.py``. Its single responsibility is
to decide which *care phase* the patient is currently in, based on signals
flowing in from other Phase 1/2/3 services (risk predictions, voice journal
crisis flags, adherence metrics, trajectory shape).

Transitions are deterministic — one snapshot in, one phase out — which
keeps the decision auditable. All transitions write a ``PhaseTransition``
row onto the state's history and publish a ``THERAPY_PHASE_CHANGED`` event
so downstream consumers (dashboard aggregator, PPO reranker, passport
renderer) can react.

Persistence
-----------
This service is persistence-agnostic. The default store is an in-memory
dict keyed by ``patient_id``; a drop-in Redis-backed store can be swapped
via ``set_store()`` once Component 2's patient database is ready. Keeping
storage pluggable means this service has zero DB coupling and unit tests
can supply a mock store.

Non-goals
---------
* Not a clinician substitute. The orchestrator never prescribes; it only
  surfaces which intervention *tones* (safety-first, skill-building, etc.)
  fit the current phase for the reranker to consume.
* Not a deterministic career oracle. Clinician overrides are always
  respected and propagated verbatim.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from schemas.synthetic.therapy_orchestrator_schema import (
    CarePathSnapshot,
    CarePathState,
    CarePhase,
    PhaseTransition,
    PhaseTrigger,
)

logger = logging.getLogger(__name__)


# ─── Static phase metadata ────────────────────────────────────────────────

_PHASE_GUIDANCE: Dict[CarePhase, str] = {
    CarePhase.INTAKE: (
        "Onboarding phase. Focus is on completing the baseline assessment, "
        "establishing trust, and agreeing goals — no interventions prescribed "
        "until stabilisation begins."
    ),
    CarePhase.STABILISE: (
        "Acute stabilisation. Keep intervention intensity conservative and "
        "review cadence short. Safety-first options (psychoeducation, gentle "
        "wellness app, breathing) are preferred over heavy interventions."
    ),
    CarePhase.PRACTICE: (
        "Skill-building phase. CBT/exercise/journaling practice is encouraged "
        "and adherence is measured. Intensity may be stepped up as tolerated."
    ),
    CarePhase.INTEGRATE: (
        "Integration phase. Skills are carried into daily life. Intensity "
        "typically eases; emphasis shifts to generalisation and relapse "
        "prevention planning."
    ),
    CarePhase.MAINTAIN: (
        "Maintenance phase. Long-interval check-ins, adherence-light. "
        "Deterioration at any point returns the patient to stabilise."
    ),
}

_PHASE_TONES: Dict[CarePhase, List[str]] = {
    CarePhase.INTAKE:    ["psychoeducation", "wellness_app", "breathing"],
    CarePhase.STABILISE: ["wellness_app", "breathing", "meditation", "sleep"],
    CarePhase.PRACTICE:  ["cbt", "exercise", "journaling", "gratitude"],
    CarePhase.INTEGRATE: ["cbt", "social_connection", "nature_walk", "exercise"],
    CarePhase.MAINTAIN:  ["gratitude", "nature_walk", "social_connection", "wellness_app"],
}

_PHASE_CADENCE_DAYS: Dict[CarePhase, int] = {
    CarePhase.INTAKE:    3,
    CarePhase.STABILISE: 3,
    CarePhase.PRACTICE:  7,
    CarePhase.INTEGRATE: 14,
    CarePhase.MAINTAIN:  30,
}


# ─── Pluggable store ──────────────────────────────────────────────────────

class _InMemoryStore:
    """Default process-local store. Thread-safe via asyncio lock."""

    def __init__(self) -> None:
        self._by_patient: Dict[str, CarePathState] = {}
        self._lock = asyncio.Lock()

    async def get(self, patient_id: str) -> Optional[CarePathState]:
        async with self._lock:
            state = self._by_patient.get(patient_id)
            # Return a copy so callers don't mutate shared state.
            return state.model_copy(deep=True) if state else None

    async def put(self, state: CarePathState) -> None:
        async with self._lock:
            self._by_patient[state.patient_id] = state.model_copy(deep=True)


_store: Any = _InMemoryStore()


def set_store(store: Any) -> None:
    """Swap the backing store (must implement ``async get/put``)."""
    global _store
    _store = store


# ─── Transition rules ─────────────────────────────────────────────────────

def _initial_phase(snapshot: CarePathSnapshot) -> CarePhase:
    """Bootstrap a never-before-seen patient.

    Default is ``intake`` — but if the snapshot clearly represents an
    already-engaged patient (non-zero journal entries, known trajectory,
    non-null risk), we skip ahead to ``stabilise`` so cold-start from
    Component 2 imports doesn't strand them in intake.
    """
    if snapshot.clinician_override:
        return snapshot.clinician_override
    has_engagement = bool(
        (snapshot.journal_entries_14d or 0) > 0
        or snapshot.trajectory_shape is not None
        or snapshot.current_risk_level is not None
    )
    return CarePhase.STABILISE if has_engagement else CarePhase.INTAKE


def _evaluate(
    state: CarePathState, snapshot: CarePathSnapshot,
) -> Tuple[CarePhase, Optional[PhaseTrigger], str, bool]:
    """Pure decision function.

    Returns ``(next_phase, trigger, rationale, safety_escalation_required)``.
    If ``trigger`` is ``None`` the phase is unchanged.
    """

    current = state.phase

    # 0. Clinician override wins over all automation.
    if snapshot.clinician_override and snapshot.clinician_override != current:
        return (
            snapshot.clinician_override,
            PhaseTrigger.CLINICIAN_OVERRIDE,
            f"Clinician-initiated move from {current.value} to "
            f"{snapshot.clinician_override.value}.",
            snapshot.clinician_override == CarePhase.STABILISE,
        )

    # 1. Crisis always raises the safety-escalation flag. If the patient
    #    isn't yet in stabilise we also route them there. If they are
    #    already in stabilise, we keep the phase but still emit the
    #    escalation so the downstream router can surface safety resources.
    if snapshot.crisis_language_detected:
        if current != CarePhase.STABILISE:
            return (
                CarePhase.STABILISE,
                PhaseTrigger.CRISIS_FLAG,
                "Crisis-language heuristic matched in recent voice journal — "
                "returning to stabilise and surfacing safety resources.",
                True,
            )
        # Already in stabilise — don't churn the phase, but flag escalation.
        return (
            current,
            None,
            "Crisis-language detected while already in stabilise — "
            "maintaining phase but raising safety escalation.",
            True,
        )

    # 2. Sharp deterioration → stabilise.
    deteriorating = (
        snapshot.trajectory_shape == "worsening"
        and (snapshot.mean_high_risk_probability or 0.0) >= 0.5
    )
    if deteriorating and current not in (CarePhase.STABILISE, CarePhase.INTAKE):
        return (
            CarePhase.STABILISE,
            PhaseTrigger.RISK_DETERIORATED,
            "Worsening trajectory combined with elevated mean high-risk "
            "probability — returning to stabilise.",
            True,
        )

    # 3. Phase-specific forward-progression rules.
    if current == CarePhase.INTAKE:
        # Intake → stabilise once we have *any* meaningful signal.
        has_signal = (
            snapshot.current_risk_level is not None
            or snapshot.trajectory_shape is not None
            or (snapshot.days_since_intake or 0) >= 3
        )
        if has_signal:
            return (
                CarePhase.STABILISE,
                PhaseTrigger.ONBOARDING_COMPLETE,
                "Onboarding signals received — moving into stabilise.",
                False,
            )

    elif current == CarePhase.STABILISE:
        improved = (
            snapshot.trajectory_shape in ("improving", "stable")
            and (snapshot.mean_high_risk_probability or 1.0) <= 0.35
        )
        if improved:
            return (
                CarePhase.PRACTICE,
                PhaseTrigger.RISK_IMPROVED,
                "Risk trajectory improving and mean high-risk probability "
                "below 35% — ready for skill-building phase.",
                False,
            )

    elif current == CarePhase.PRACTICE:
        # Need both adherence AND engagement to progress.
        enough_adherence = (snapshot.adherence_rate or 0.0) >= 0.70
        enough_engagement = (snapshot.journal_entries_14d or 0) >= 5
        low_risk = (snapshot.mean_high_risk_probability or 1.0) <= 0.30
        if enough_adherence and enough_engagement and low_risk:
            return (
                CarePhase.INTEGRATE,
                PhaseTrigger.SKILL_PRACTISED,
                "Adherence ≥70% with ≥5 journal entries in the last 14 days "
                "and risk stable — moving into integrate.",
                False,
            )
        # Only step down on *measured* low adherence. ``None`` means the
        # caller hasn't computed it yet — treat that as "no signal" rather
        # than "zero adherence" to avoid spurious regressions.
        if snapshot.adherence_rate is not None and snapshot.adherence_rate <= 0.30:
            return (
                CarePhase.STABILISE,
                PhaseTrigger.ADHERENCE_LOW,
                "Adherence ≤30% in practice phase — stepping back to "
                "stabilise and simplifying the plan.",
                False,
            )

    elif current == CarePhase.INTEGRATE:
        # Integrate → maintain after a sustained period of low risk & adherence.
        sustained = (
            (snapshot.days_since_intake or 0) >= 90
            and (snapshot.adherence_rate or 0.0) >= 0.60
            and (snapshot.mean_high_risk_probability or 1.0) <= 0.30
        )
        if sustained:
            return (
                CarePhase.MAINTAIN,
                PhaseTrigger.TIME_ELAPSED,
                "≥90 days in care with sustained adherence and low risk — "
                "transitioning to maintenance.",
                False,
            )

    elif current == CarePhase.MAINTAIN:
        # Routine drift — if trajectory starts worsening without hitting the
        # high-severity criteria above, drop to practice for a refresher.
        if snapshot.trajectory_shape == "worsening":
            return (
                CarePhase.PRACTICE,
                PhaseTrigger.RISK_DETERIORATED,
                "Maintenance drift detected — returning to practice for a "
                "skills refresher.",
                False,
            )

    return current, None, "No transition criteria met.", False


# ─── Public orchestration ────────────────────────────────────────────────

async def transition(
    snapshot: CarePathSnapshot,
    *,
    event_publisher: Optional[Callable[[str, Dict[str, Any]], Awaitable[Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Process a snapshot and return the (possibly updated) state + guidance.

    ``event_publisher`` is injected so tests can omit the event bus. If
    omitted in production, we defer-import from ``lib.infra.event_bus`` so
    the service's own test surface doesn't require the bus either.
    """
    now = now or datetime.utcnow()
    existing = await _store.get(snapshot.patient_id)

    if existing is None:
        start_phase = _initial_phase(snapshot)
        state = CarePathState(
            patient_id=snapshot.patient_id,
            phase=start_phase,
            phase_started_at=now,
            updated_at=now,
            history=[
                PhaseTransition(
                    from_phase=None, to_phase=start_phase,
                    trigger=(
                        PhaseTrigger.CLINICIAN_OVERRIDE
                        if snapshot.clinician_override else PhaseTrigger.ONBOARDING_COMPLETE
                    ),
                    at=now,
                    rationale=f"Initial phase assignment on first snapshot ({start_phase.value}).",
                )
            ],
            notes=[],
        )
        transitioned = True
        safety_escalation_required = start_phase == CarePhase.STABILISE and (
            snapshot.crisis_language_detected or snapshot.current_risk_level == "high"
        )
    else:
        next_phase, trigger, rationale, safety_escalation_required = _evaluate(existing, snapshot)
        if trigger is None or next_phase == existing.phase:
            state = existing.model_copy(deep=True)
            state.updated_at = now
            transitioned = False
        else:
            state = existing.model_copy(deep=True)
            state.phase = next_phase
            state.phase_started_at = now
            state.updated_at = now
            state.history.append(
                PhaseTransition(
                    from_phase=existing.phase, to_phase=next_phase,
                    trigger=trigger, at=now, rationale=rationale,
                )
            )
            transitioned = True
            logger.info(
                "care_phase_transitioned",
                extra={
                    "patient_id": state.patient_id,
                    "from_phase": existing.phase.value,
                    "to_phase": next_phase.value,
                    "trigger": trigger.value,
                },
            )

    # History grows unbounded otherwise — keep only the most recent 50 entries.
    if len(state.history) > 50:
        state.history = state.history[-50:]

    await _store.put(state)

    # Publish transition event (never block on bus failures).
    if transitioned:
        try:
            if event_publisher is None:
                from lib.infra.event_bus import Topics, publish as bus_publish
                await bus_publish(Topics.THERAPY_PHASE_CHANGED, {
                    "patient_id": state.patient_id,
                    "phase": state.phase.value,
                    "safety_escalation_required": safety_escalation_required,
                })
            else:
                await event_publisher("therapy.phase_changed", {
                    "patient_id": state.patient_id,
                    "phase": state.phase.value,
                    "safety_escalation_required": safety_escalation_required,
                })
        except Exception as exc:  # pragma: no cover — event bus best-effort
            logger.info("therapy_phase_event_failed", extra={"error": str(exc)})

    phase_guidance = _PHASE_GUIDANCE[state.phase]
    tones = list(_PHASE_TONES[state.phase])
    cadence = _PHASE_CADENCE_DAYS[state.phase]
    if safety_escalation_required:
        tones.insert(0, "safety_review")

    return {
        "state": state,
        "transitioned": transitioned,
        "phase_guidance": phase_guidance,
        "recommended_intervention_tones": tones,
        "review_cadence_days": cadence,
        "safety_escalation_required": safety_escalation_required,
    }


async def get_state(patient_id: str) -> Optional[CarePathState]:
    return await _store.get(patient_id)


async def reset_for_tests() -> None:
    """Test hook — wipes the store. Never invoked in production."""
    global _store
    _store = _InMemoryStore()
