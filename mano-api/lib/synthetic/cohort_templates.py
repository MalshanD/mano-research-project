"""
Pre-built cohort generation templates.

Researchers asking for synthetic cohorts spend a measurable amount of
time in "compose-the-request" friction: figuring out the right seed,
the right size, the right epsilon, what TimeGAN should and shouldn't
include. The templates here remove that friction for the most common
research scenarios.

Each template is a ready-shaped ``CohortGenerateRequest``. Researchers
pick a template name, optionally override the size or seed, and ship.

Templates are deliberately small and explicit. They live in code (not a
DB table) so a code review is required to add a new one, which keeps
the catalog disciplined.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from schemas.synthetic.research_cohort_schema import (
    CohortFormat,
    CohortGenerateRequest,
)


# ─── Template descriptors ────────────────────────────────────────────────────


@dataclass(frozen=True)
class CohortTemplate:
    name: str
    title: str
    description: str
    research_use_case: str
    defaults: Dict[str, object]
    privacy_notes: str


_TEMPLATES: Dict[str, CohortTemplate] = {
    "anxious_adults_25_35_balanced_gender": CohortTemplate(
        name="anxious_adults_25_35_balanced_gender",
        title="Anxious adults 25–35 — balanced gender",
        description=(
            "200 synthetic adults aged 25–35 with elevated anxiety scores, "
            "balanced across gender. TimeGAN sequences included so the "
            "downstream LSTM can be exercised against realistic vitals."
        ),
        research_use_case=(
            "Pilot studies testing CBT-vs-mindfulness interventions on a "
            "high-anxiety young-adult population without exposing real "
            "patient records."
        ),
        defaults={
            "num_patients": 200,
            "include_timegan": True,
            "output_format": CohortFormat.BOTH,
            "epsilon": 5.0,
            "notes": "Template: anxious_adults_25_35_balanced_gender",
        },
        privacy_notes=(
            "Epsilon 5.0 is a moderate privacy budget; tighten to 1.0 for "
            "external sharing. Audit AUC must remain ≤ 0.55 for this "
            "cohort to be approved for external release."
        ),
    ),
    "stable_elderly_low_risk_baseline": CohortTemplate(
        name="stable_elderly_low_risk_baseline",
        title="Stable elderly — low-risk baseline",
        description=(
            "150 synthetic adults aged 60+ with stable mental-health "
            "indicators. Useful as a control arm for trials whose primary "
            "outcome is preventing decline rather than treating acute "
            "distress."
        ),
        research_use_case=(
            "Control-arm matching for prevention trials, or as a "
            "comparator to age-matched high-risk cohorts when assessing "
            "intervention specificity."
        ),
        defaults={
            "num_patients": 150,
            "include_timegan": True,
            "output_format": CohortFormat.BOTH,
            "epsilon": 5.0,
            "notes": "Template: stable_elderly_low_risk_baseline",
        },
        privacy_notes=(
            "Older-adult cohorts are smaller than the population — "
            "k-anonymity is more sensitive. Audit min_k must be ≥ 5 for "
            "this cohort to be approved for external release."
        ),
    ),
    "seasonal_depression_winter_cohort": CohortTemplate(
        name="seasonal_depression_winter_cohort",
        title="Seasonal depression — winter cohort",
        description=(
            "180 synthetic adults reporting low mood with reduced sleep "
            "quality and stress elevation typical of seasonal affective "
            "disorder presentations. TimeGAN included."
        ),
        research_use_case=(
            "Studies of light therapy, vitamin D supplementation, or "
            "exercise interventions targeted at seasonal depression. "
            "Pairs naturally with the weather/SAD service."
        ),
        defaults={
            "num_patients": 180,
            "include_timegan": True,
            "output_format": CohortFormat.BOTH,
            "epsilon": 5.0,
            "notes": "Template: seasonal_depression_winter_cohort",
        },
        privacy_notes=(
            "Geographic skew can introduce re-identification risk when "
            "this cohort is paired with weather context. Strip "
            "weather-station codes before external sharing."
        ),
    ),
    "adolescent_high_screen_time_high_anxiety": CohortTemplate(
        name="adolescent_high_screen_time_high_anxiety",
        title="Adolescents — high screen time, high anxiety",
        description=(
            "120 synthetic adolescents (13–17) with elevated screen-time "
            "exposure and anxiety scores. This cohort exercises the most "
            "out-of-distribution edge of CTGAN's training data; expect "
            "wider audit-band severities."
        ),
        research_use_case=(
            "Hypothesis-generating studies on the relationship between "
            "screen-time exposure and anxiety in adolescents. Should be "
            "reviewed by an IRB before being treated as conclusive."
        ),
        defaults={
            "num_patients": 120,
            "include_timegan": True,
            "output_format": CohortFormat.BOTH,
            "epsilon": 3.0,
            "notes": "Template: adolescent_high_screen_time_high_anxiety",
        },
        privacy_notes=(
            "Adolescent data carries elevated regulatory weight (e.g. "
            "GDPR-K, COPPA). Tightened epsilon (3.0) and a stricter "
            "audit pass (overall_severity must be OK) are required for "
            "external sharing."
        ),
    ),
    "pre_post_intervention_matched_pair": CohortTemplate(
        name="pre_post_intervention_matched_pair",
        title="Pre/post intervention — matched pair",
        description=(
            "100 synthetic patients sampled twice (same seed family, "
            "different perturbations) to model a matched pre/post "
            "intervention pair. Use the second cohort to simulate the "
            "post-intervention state."
        ),
        research_use_case=(
            "Power calculations and effect-size projections for "
            "before/after intervention studies, without recruiting real "
            "subjects up front."
        ),
        defaults={
            "num_patients": 100,
            "include_timegan": True,
            "output_format": CohortFormat.BOTH,
            "epsilon": 5.0,
            "notes": "Template: pre_post_intervention_matched_pair (set 1 of 2)",
        },
        privacy_notes=(
            "Matched-pair studies require two cohorts generated with "
            "different seeds drawn from a known family. Document the seed "
            "lineage in the manifest notes for reproducibility. The audit "
            "must pass on BOTH cohorts independently — paired cohorts can "
            "leak more than the sum of their parts when joined, so re-run "
            "the audit on a join sample before external sharing."
        ),
    ),
}


# ─── Public helpers ──────────────────────────────────────────────────────────


def list_templates() -> List[Dict[str, str]]:
    """Return a list of template descriptors for catalog rendering."""
    return [
        {
            "name": t.name,
            "title": t.title,
            "description": t.description,
            "research_use_case": t.research_use_case,
            "privacy_notes": t.privacy_notes,
        }
        for t in _TEMPLATES.values()
    ]


def get_template(name: str) -> CohortTemplate:
    """Look up a template by name; raises KeyError if unknown."""
    if name not in _TEMPLATES:
        raise KeyError(
            f"Unknown cohort template: {name!r}. "
            f"Available: {sorted(_TEMPLATES.keys())}"
        )
    return _TEMPLATES[name]


def build_request(
    name: str,
    *,
    researcher_id: str,
    overrides: Optional[Dict[str, object]] = None,
) -> CohortGenerateRequest:
    """Compose a ``CohortGenerateRequest`` from a template + the
    researcher's identifier + any per-call overrides.

    The researcher_id must always be supplied — the template doesn't
    encode it (it's a per-call attribute, not a template attribute).
    Overrides are applied last and win over template defaults.
    """
    template = get_template(name)
    payload: Dict[str, object] = {"researcher_id": researcher_id}
    payload.update(template.defaults)
    if overrides:
        payload.update(overrides)
    return CohortGenerateRequest(**payload)
    template = get_template(name)
    payload: Dict[str, object] = {"researcher_id": researcher_id}
    payload.update(template.defaults)
    if overrides:
        payload.update(overrides)
    return CohortGenerateRequest(**payload)
