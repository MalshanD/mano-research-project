"""
Schemas for the PPO Reranker.

What this is
------------
The existing ``/api/v1/nba/recommend`` endpoint already ranks interventions
by simulator-predicted risk reduction. The reranker adds a second pass:

1. Start from a candidate pool (supplied by the caller *or* derived from
   the NBA's simulator pass).
2. Score each candidate along multiple axes — PPO policy probability,
   simulator risk reduction, adherence prior, care-phase prior, safety
   veto — and blend with an explicit, inspectable weight vector.
3. Return a ranked list with a per-candidate explanation string built from
   the highest-weighted contributing factors.

This is deliberately *not* a model retrain. Weights are declared at the
service level and can be tuned without touching the frozen PPO or the
frozen Seq2Seq simulator.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import PatientState


class RerankerWeights(BaseModel):
    """Inspectable weight vector for the rerank blend.

    Callers may supply either (a) weights that already sum to 1.0, or
    (b) *relative* weights (e.g. 2/4/2/1/1) that the service will
    normalise before use. For that reason we only enforce ``ge=0.0``
    here; ``_validate_weights`` in the service layer handles
    normalisation + the zero-sum check. Using a Pydantic model makes
    the weights visible in the OpenAPI docs — clinicians / researchers
    can see the exact blend, not guess at a hidden formula.
    """
    w_ppo_policy: float = Field(default=0.25, ge=0.0)
    w_simulator_risk_reduction: float = Field(default=0.35, ge=0.0)
    w_adherence_prior: float = Field(default=0.15, ge=0.0)
    w_care_phase_prior: float = Field(default=0.15, ge=0.0)
    w_patient_preference: float = Field(default=0.10, ge=0.0)


class AdherencePrior(BaseModel):
    """Optional per-intervention adherence priors (0..1).

    Keys are lowercase intervention names (e.g. 'cbt', 'exercise'). Missing
    keys default to 0.5 (neutral). Populated from the patient's recent
    interaction history by Component 2.
    """
    wellness_app: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cbt: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exercise: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    medication: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    control: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PatientPreferences(BaseModel):
    """Soft patient preference weights.

    Same key convention as ``AdherencePrior``. A value of 0.0 does NOT
    disqualify an intervention — it just reduces the ranking weight. Use
    ``contraindications`` for hard safety excludes.
    """
    wellness_app: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cbt: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exercise: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    medication: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    control: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RerankerRequest(BaseModel):
    patient_state: PatientState
    care_phase: Literal[
        "intake", "stabilise", "practice", "integrate", "maintain"
    ] = Field(
        default="stabilise",
        description="Current care phase from the therapy orchestrator.",
    )
    adherence: Optional[AdherencePrior] = None
    preferences: Optional[PatientPreferences] = None
    contraindications: List[
        Literal["wellness_app", "cbt", "exercise", "medication", "control"]
    ] = Field(
        default_factory=list,
        description="Hard excludes. These never appear in the ranked output.",
    )
    weights: Optional[RerankerWeights] = None
    top_k: int = Field(default=5, ge=1, le=5)


class RerankedCandidate(BaseModel):
    intervention_id: int
    intervention_name: str
    intensity: float = Field(..., ge=0.0, le=1.0)

    # Axis scores — all normalised to [0, 1] before blending.
    ppo_policy_score: float = Field(..., ge=0.0, le=1.0)
    simulator_risk_reduction_score: float = Field(..., ge=0.0, le=1.0)
    adherence_prior_score: float = Field(..., ge=0.0, le=1.0)
    care_phase_prior_score: float = Field(..., ge=0.0, le=1.0)
    patient_preference_score: float = Field(..., ge=0.0, le=1.0)

    # Raw simulator risk reduction — the headline metric clinicians actually
    # read (unlike the normalised score).
    raw_risk_reduction: float = Field(
        ..., description="Baseline high-risk probability minus simulated future's.",
    )

    final_score: float = Field(..., ge=0.0, le=1.0)
    rank: int
    explanation: str
    contributing_factors: List[str] = Field(default_factory=list)


class RerankerResponse(BaseModel):
    ppo_top_pick: str = Field(..., description="Name of the PPO's unblended pick.")
    ppo_confidence: float = Field(..., ge=0.0, le=1.0)
    weights: RerankerWeights
    candidates: List[RerankedCandidate]
    blocked: List[str] = Field(
        default_factory=list,
        description="Interventions removed by contraindication — exposed for audit/UX.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Human-readable context messages (e.g. zero-simulator-delta warnings).",
    )
