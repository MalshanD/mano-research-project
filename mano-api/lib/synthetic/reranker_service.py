"""
PPO Reranker service.

Pipeline
--------
1. **Parse patient state** via the shared ``state_parser`` helpers — same
   flatten / static-vector conventions used by the simulator and LSTM.
2. **Ask the PPO agent** for its pick + confidence. The agent was loaded
   once at boot into ``InterventionService``; we don't retrain or mutate
   its weights.
3. **Expand the PPO's policy head** to a full softmax over all five
   interventions so every candidate gets a policy score, not just the
   argmax. This is a cheap additive inspection of the frozen network —
   no retraining.
4. **Simulate every candidate** at the PPO's intensity (identical to the
   existing ``nba_router`` pass) and compute raw ``risk_reduction``.
5. **Apply priors** — adherence, care-phase, patient preference. Each is
   a [0, 1] score; missing signals collapse to a neutral 0.5.
6. **Blend** via the declared ``RerankerWeights`` vector (defaults can be
   overridden per-request for ablations).
7. **Explain** — the top 3 contributing axes (by weight × score) become the
   candidate's explanation string.

All five axis scores are returned verbatim so the frontend can render a
radar chart or equivalent without re-deriving them.

Why keep this separate from ``nba_router``?
-------------------------------------------
* ``nba_router`` produces a simulator-only ranking plus a PPO "did you
  agree?" flag. It's load-bearing for the existing frontend — we mustn't
  change its response shape.
* The reranker is v2: richer output, adherence + preference blending,
  explainability. Lives alongside the legacy NBA route, additively.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import parse_patient_state
from schemas.synthetic.reranker_schema import (
    AdherencePrior,
    PatientPreferences,
    RerankedCandidate,
    RerankerRequest,
    RerankerResponse,
    RerankerWeights,
)
from schemas.synthetic.simulation_schema import PatientState

logger = logging.getLogger(__name__)


INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]
INTERVENTION_SLUGS = ["control", "wellness_app", "cbt", "exercise", "medication"]
NUM_INTERVENTIONS = len(INTERVENTION_NAMES)


# ─── Care-phase priors ───────────────────────────────────────────────────
#
# These mirror the care-path orchestrator's "recommended tones" table,
# translated from tone strings into per-intervention scores. Tight coupling
# to the orchestrator's data is deliberate — both surfaces must agree on
# what each phase calls for.

_CARE_PHASE_PRIORS: Dict[str, Dict[str, float]] = {
    "intake":    {"control": 0.9, "wellness_app": 0.7, "cbt": 0.4, "exercise": 0.3, "medication": 0.1},
    "stabilise": {"control": 0.5, "wellness_app": 0.8, "cbt": 0.5, "exercise": 0.4, "medication": 0.6},
    "practice":  {"control": 0.2, "wellness_app": 0.6, "cbt": 0.9, "exercise": 0.8, "medication": 0.5},
    "integrate": {"control": 0.3, "wellness_app": 0.5, "cbt": 0.7, "exercise": 0.8, "medication": 0.4},
    "maintain":  {"control": 0.6, "wellness_app": 0.5, "cbt": 0.4, "exercise": 0.6, "medication": 0.3},
}


# ─── Weight validation ──────────────────────────────────────────────────

def _validate_weights(weights: RerankerWeights) -> RerankerWeights:
    total = (
        weights.w_ppo_policy
        + weights.w_simulator_risk_reduction
        + weights.w_adherence_prior
        + weights.w_care_phase_prior
        + weights.w_patient_preference
    )
    if total <= 0:
        raise ValueError("All reranker weights are zero.")
    # Normalise so callers can pass relative weights without summing to 1.0.
    return RerankerWeights(
        w_ppo_policy=weights.w_ppo_policy / total,
        w_simulator_risk_reduction=weights.w_simulator_risk_reduction / total,
        w_adherence_prior=weights.w_adherence_prior / total,
        w_care_phase_prior=weights.w_care_phase_prior / total,
        w_patient_preference=weights.w_patient_preference / total,
    )


# ─── PPO policy probability vector ──────────────────────────────────────

def _ppo_policy_vector(
    int_service: InterventionService, dyn_flat: np.ndarray, stat_flat: np.ndarray,
) -> Tuple[np.ndarray, int, float, float]:
    """Return ``(policy_probs[5], ppo_action_id, ppo_intensity, ppo_confidence)``.

    Cheap additive inspection of the frozen agent — we call ``agent.act``
    for the deterministic pick, then independently evaluate the actor's
    softmax over the full action space.
    """
    if int_service.agent is None:
        raise RuntimeError("PPO agent not loaded")

    state = np.concatenate([dyn_flat, stat_flat]).astype(np.float32)
    state_tensor = torch.FloatTensor(state).to(int_service.device)
    with torch.no_grad():
        (action_cat, action_cont), _, _ = int_service.agent.act(state_tensor)
        # Full softmax — we re-derive it so we don't rely on a side-effect of ``act``.
        features = int_service.agent.features(state_tensor.unsqueeze(0))
        logits = int_service.agent.actor_discrete(features)
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

    action_id = int(action_cat)
    intensity = float(action_cont)
    confidence = float(probs[action_id])
    return probs, action_id, intensity, confidence


# ─── Score derivation helpers ───────────────────────────────────────────

def _normalise_risk_reduction(raw: float) -> float:
    """Clamp to [-0.5, 0.5] then map to [0, 1].

    The LSTM's high-risk probability lives in [0, 1], so the max feasible
    risk reduction (best future minus worst present) is 1.0. In practice
    values cluster much tighter; we use a ±0.5 window so the axis stays
    discriminating.
    """
    clamped = max(-0.5, min(0.5, raw))
    return (clamped + 0.5)  # → [0, 1]


def _adherence_score(adherence: Optional[AdherencePrior], slug: str) -> float:
    if adherence is None:
        return 0.5
    val = getattr(adherence, slug, None)
    return float(val) if val is not None else 0.5


def _preference_score(prefs: Optional[PatientPreferences], slug: str) -> float:
    if prefs is None:
        return 0.5
    val = getattr(prefs, slug, None)
    return float(val) if val is not None else 0.5


def _care_phase_score(phase: str, slug: str) -> float:
    return float(_CARE_PHASE_PRIORS.get(phase, {}).get(slug, 0.5))


def _format_intervention_phrase(slug: str, score: float) -> str:
    direction = "strongly supports" if score >= 0.75 else (
        "supports" if score >= 0.55 else (
            "is neutral on" if score >= 0.45 else (
                "weakly discourages" if score >= 0.25 else "strongly discourages"
            )
        )
    )
    return direction


def _explanation(
    weights: RerankerWeights,
    slug: str,
    scores: Dict[str, float],
    intervention_name: str,
) -> Tuple[str, List[str]]:
    """Pick the 3 highest weight × score contributors and render a sentence."""
    contributions = [
        ("PPO policy", weights.w_ppo_policy * scores["ppo_policy_score"]),
        ("simulator risk reduction", weights.w_simulator_risk_reduction * scores["simulator_risk_reduction_score"]),
        ("adherence prior", weights.w_adherence_prior * scores["adherence_prior_score"]),
        ("care-phase prior", weights.w_care_phase_prior * scores["care_phase_prior_score"]),
        ("patient preference", weights.w_patient_preference * scores["patient_preference_score"]),
    ]
    contributions.sort(key=lambda kv: kv[1], reverse=True)
    top = contributions[:3]

    # Short, plain-language explanation. We phrase relative to the
    # intervention, not abstract axis names, so clinicians can read it.
    top_names = [name for name, _ in top]
    factor_str = ", ".join(top_names[:-1]) + f", and {top_names[-1]}" if len(top_names) > 1 else top_names[0]
    return (
        f"{intervention_name} ranked by {factor_str}.",
        top_names,
    )


def _safety_blocks(
    contraindications: List[str],
    care_phase: str,
) -> List[str]:
    """Return the set of interventions to block in addition to the caller's."""
    blocked = set(contraindications)
    # Conservative guard: during the intake phase, medication recommendations
    # must always be clinician-initiated. The caller can still request them
    # via an explicit empty contraindications list after overriding phase.
    if care_phase == "intake":
        blocked.add("medication")
    return sorted(blocked)


# ─── Public entrypoint ───────────────────────────────────────────────────

async def rerank(request: RerankerRequest) -> RerankerResponse:
    """Rerank the five interventions for this patient + context."""
    int_service = InterventionService()
    risk_service = RiskPredictionService()

    if int_service.agent is None or int_service.simulator is None:
        raise RuntimeError("Intervention service not loaded (agent or simulator missing).")
    if risk_service.model is None:
        raise RuntimeError("Risk prediction service not loaded.")

    weights = _validate_weights(request.weights or RerankerWeights())
    blocked = _safety_blocks(request.contraindications, request.care_phase)
    notes: List[str] = []
    if blocked:
        notes.append(f"Blocked by safety/contraindication: {', '.join(blocked)}")

    # 1. Parse state once.
    dyn_np, stat_np = parse_patient_state(request.patient_state)
    dyn_flat = dyn_np.flatten()
    stat_flat = stat_np.flatten()

    # 2. Baseline risk.
    baseline = risk_service.predict(dyn_np, stat_np)
    baseline_high = float(baseline["probabilities"][2])

    # 3. PPO policy probabilities.
    probs, ppo_action, ppo_intensity, ppo_confidence = _ppo_policy_vector(
        int_service, dyn_flat, stat_flat,
    )

    # 4. Simulate every (non-blocked) candidate at PPO's intensity.
    candidates: List[RerankedCandidate] = []
    for int_id in range(NUM_INTERVENTIONS):
        slug = INTERVENTION_SLUGS[int_id]
        name = INTERVENTION_NAMES[int_id]
        if slug in blocked:
            continue

        try:
            future_np = int_service.simulate_outcome(dyn_np, int_id, ppo_intensity)
            future_risk = risk_service.predict(future_np, stat_np)
            future_high = float(future_risk["probabilities"][2])
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "reranker_sim_failed",
                extra={"intervention": name, "error": str(exc)},
            )
            continue
        raw_rr = baseline_high - future_high

        ppo_score = float(probs[int_id])
        sim_score = _normalise_risk_reduction(raw_rr)
        adh_score = _adherence_score(request.adherence, slug)
        phase_score = _care_phase_score(request.care_phase, slug)
        pref_score = _preference_score(request.preferences, slug)

        scores = {
            "ppo_policy_score": ppo_score,
            "simulator_risk_reduction_score": sim_score,
            "adherence_prior_score": adh_score,
            "care_phase_prior_score": phase_score,
            "patient_preference_score": pref_score,
        }
        final = (
            weights.w_ppo_policy * ppo_score
            + weights.w_simulator_risk_reduction * sim_score
            + weights.w_adherence_prior * adh_score
            + weights.w_care_phase_prior * phase_score
            + weights.w_patient_preference * pref_score
        )
        explanation, contributing = _explanation(weights, slug, scores, name)

        candidates.append(RerankedCandidate(
            intervention_id=int_id,
            intervention_name=name,
            intensity=round(ppo_intensity, 3),
            ppo_policy_score=round(ppo_score, 4),
            simulator_risk_reduction_score=round(sim_score, 4),
            adherence_prior_score=round(adh_score, 4),
            care_phase_prior_score=round(phase_score, 4),
            patient_preference_score=round(pref_score, 4),
            raw_risk_reduction=round(raw_rr, 4),
            final_score=round(max(0.0, min(1.0, final)), 4),
            rank=0,  # filled in after sort
            explanation=explanation,
            contributing_factors=contributing,
        ))

    # 5. Rank, trim to top_k.
    candidates.sort(key=lambda c: c.final_score, reverse=True)
    candidates = candidates[: request.top_k]
    for rank, c in enumerate(candidates, start=1):
        c.rank = rank

    ppo_top_pick_name = INTERVENTION_NAMES[ppo_action] if 0 <= ppo_action < NUM_INTERVENTIONS else "Unknown"
    agreement = bool(candidates and candidates[0].intervention_id == ppo_action)

    logger.info(
        "reranker_complete",
        extra={
            "ppo_pick": ppo_top_pick_name,
            "top_rerank": candidates[0].intervention_name if candidates else "none",
            "agreement": agreement,
            "blocked": blocked,
            "care_phase": request.care_phase,
        },
    )

    return RerankerResponse(
        ppo_top_pick=ppo_top_pick_name,
        ppo_confidence=round(ppo_confidence, 4),
        weights=weights,
        candidates=candidates,
        blocked=blocked,
        agreement_with_ppo=agreement,
        notes=notes,
    )
