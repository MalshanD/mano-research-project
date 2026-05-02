"""
Care-Path Therapy Orchestrator tests.

Focused on the pure decision function ``_evaluate`` (no I/O, no event
bus) plus a handful of integration tests through the public ``transition``
entrypoint so we catch persistence + history bugs.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lib.synthetic.therapy_orchestrator_service import (
    _evaluate,
    _initial_phase,
    reset_for_tests,
    transition,
)
from schemas.synthetic.therapy_orchestrator_schema import (
    CarePathSnapshot,
    CarePathState,
    CarePhase,
    PhaseTrigger,
)


@pytest.fixture(autouse=True)
async def _reset():
    await reset_for_tests()
    yield
    await reset_for_tests()


def _state(phase: CarePhase) -> CarePathState:
    now = datetime.now(timezone.utc)
    return CarePathState(
        patient_id="p-test",
        phase=phase,
        phase_started_at=now,
        updated_at=now,
    )


# ─── _initial_phase ──────────────────────────────────────────────────────

class TestInitialPhase:
    def test_cold_start_goes_to_intake(self):
        snap = CarePathSnapshot(patient_id="p-test")
        assert _initial_phase(snap) == CarePhase.INTAKE

    def test_clinician_override_wins(self):
        snap = CarePathSnapshot(patient_id="p-test", clinician_override=CarePhase.PRACTICE)
        assert _initial_phase(snap) == CarePhase.PRACTICE

    def test_engaged_patient_skips_to_stabilise(self):
        snap = CarePathSnapshot(patient_id="p-test", journal_entries_14d=3)
        assert _initial_phase(snap) == CarePhase.STABILISE


# ─── _evaluate rules ─────────────────────────────────────────────────────

class TestEvaluateRules:
    def test_clinician_override_beats_automation(self):
        state = _state(CarePhase.MAINTAIN)
        snap = CarePathSnapshot(
            patient_id="p",
            clinician_override=CarePhase.STABILISE,
            trajectory_shape="improving",  # would normally keep them in maintain
        )
        next_phase, trigger, _, escalate = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.CLINICIAN_OVERRIDE
        assert escalate is True  # override → stabilise always escalates

    def test_crisis_routes_to_stabilise(self):
        state = _state(CarePhase.PRACTICE)
        snap = CarePathSnapshot(patient_id="p", crisis_language_detected=True)
        next_phase, trigger, _, escalate = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.CRISIS_FLAG
        assert escalate is True

    def test_crisis_in_stabilise_is_noop(self):
        state = _state(CarePhase.STABILISE)
        snap = CarePathSnapshot(patient_id="p", crisis_language_detected=True)
        next_phase, trigger, _, _ = _evaluate(state, snap)
        # Already in stabilise — no transition.
        assert trigger is None
        assert next_phase == CarePhase.STABILISE

    def test_worsening_with_high_risk_deescalates(self):
        state = _state(CarePhase.INTEGRATE)
        snap = CarePathSnapshot(
            patient_id="p",
            trajectory_shape="worsening",
            mean_high_risk_probability=0.7,
        )
        next_phase, trigger, _, escalate = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.RISK_DETERIORATED
        assert escalate is True

    def test_intake_to_stabilise_after_any_signal(self):
        state = _state(CarePhase.INTAKE)
        snap = CarePathSnapshot(patient_id="p", current_risk_level="low")
        next_phase, trigger, _, _ = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.ONBOARDING_COMPLETE

    def test_intake_time_elapsed_also_progresses(self):
        state = _state(CarePhase.INTAKE)
        snap = CarePathSnapshot(patient_id="p", days_since_intake=4)
        next_phase, trigger, _, _ = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.ONBOARDING_COMPLETE

    def test_stabilise_to_practice_needs_improvement(self):
        state = _state(CarePhase.STABILISE)
        ok_snap = CarePathSnapshot(
            patient_id="p",
            trajectory_shape="improving",
            mean_high_risk_probability=0.25,
        )
        next_phase, trigger, _, _ = _evaluate(state, ok_snap)
        assert next_phase == CarePhase.PRACTICE
        assert trigger == PhaseTrigger.RISK_IMPROVED

    def test_stabilise_improving_but_risk_too_high_stays(self):
        state = _state(CarePhase.STABILISE)
        snap = CarePathSnapshot(
            patient_id="p",
            trajectory_shape="improving",
            mean_high_risk_probability=0.55,  # above the 0.35 cutoff
        )
        _, trigger, _, _ = _evaluate(state, snap)
        assert trigger is None

    def test_practice_to_integrate_requires_all_three_criteria(self):
        state = _state(CarePhase.PRACTICE)
        good = CarePathSnapshot(
            patient_id="p",
            adherence_rate=0.8,
            journal_entries_14d=6,
            mean_high_risk_probability=0.25,
        )
        next_phase, trigger, _, _ = _evaluate(state, good)
        assert next_phase == CarePhase.INTEGRATE
        assert trigger == PhaseTrigger.SKILL_PRACTISED

    def test_practice_low_adherence_steps_down(self):
        state = _state(CarePhase.PRACTICE)
        snap = CarePathSnapshot(patient_id="p", adherence_rate=0.2)
        next_phase, trigger, _, _ = _evaluate(state, snap)
        assert next_phase == CarePhase.STABILISE
        assert trigger == PhaseTrigger.ADHERENCE_LOW

    def test_integrate_to_maintain_requires_90_days_plus_adherence(self):
        state = _state(CarePhase.INTEGRATE)
        snap = CarePathSnapshot(
            patient_id="p",
            days_since_intake=120,
            adherence_rate=0.7,
            mean_high_risk_probability=0.2,
        )
        next_phase, trigger, _, _ = _evaluate(state, snap)
        assert next_phase == CarePhase.MAINTAIN
        assert trigger == PhaseTrigger.TIME_ELAPSED

    def test_maintain_worsening_drops_to_practice(self):
        state = _state(CarePhase.MAINTAIN)
        snap = CarePathSnapshot(patient_id="p", trajectory_shape="worsening")
        next_phase, trigger, _, _ = _evaluate(state, snap)
        assert next_phase == CarePhase.PRACTICE
        assert trigger == PhaseTrigger.RISK_DETERIORATED

    def test_no_signals_is_noop(self):
        state = _state(CarePhase.PRACTICE)
        snap = CarePathSnapshot(patient_id="p")
        next_phase, trigger, rationale, escalate = _evaluate(state, snap)
        assert next_phase == CarePhase.PRACTICE
        assert trigger is None
        assert escalate is False
        assert "No transition" in rationale


# ─── transition() integration ────────────────────────────────────────────

class TestTransitionIntegration:
    @pytest.mark.asyncio
    async def test_first_call_creates_state_at_intake(self):
        result = await transition(CarePathSnapshot(patient_id="p-new"))
        assert result["state"].phase == CarePhase.INTAKE
        # First call for a brand new patient should NOT count as a transition
        # from a prior state — but the initial_phase bootstrap *is* recorded.
        # Check the history captured that creation event.
        assert len(result["state"].history) >= 1
        assert result["state"].history[0].to_phase == CarePhase.INTAKE

    @pytest.mark.asyncio
    async def test_subsequent_transition_appends_history(self):
        pid = "p-history"
        # First — starts at intake
        await transition(CarePathSnapshot(patient_id=pid))
        # Second — provide a signal that forces intake → stabilise
        r2 = await transition(CarePathSnapshot(
            patient_id=pid, current_risk_level="medium",
        ))
        assert r2["transitioned"] is True
        assert r2["state"].phase == CarePhase.STABILISE
        transitions = [h.trigger for h in r2["state"].history]
        assert PhaseTrigger.ONBOARDING_COMPLETE in transitions

    @pytest.mark.asyncio
    async def test_response_contains_guidance_and_cadence(self):
        result = await transition(CarePathSnapshot(patient_id="p-guide"))
        assert result["phase_guidance"]
        assert isinstance(result["recommended_intervention_tones"], list)
        assert 1 <= result["review_cadence_days"] <= 90

    @pytest.mark.asyncio
    async def test_crisis_flag_sets_safety_escalation(self):
        pid = "p-crisis"
        # Get them into practice first
        await transition(CarePathSnapshot(patient_id=pid))
        await transition(CarePathSnapshot(
            patient_id=pid, trajectory_shape="improving",
            mean_high_risk_probability=0.2,
        ))
        # Now trip the crisis flag
        result = await transition(CarePathSnapshot(
            patient_id=pid, crisis_language_detected=True,
        ))
        assert result["state"].phase == CarePhase.STABILISE
        assert result["safety_escalation_required"] is True
