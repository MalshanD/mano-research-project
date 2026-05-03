"""
Page-bundle response schemas for the consumer-facing 6-page nav.

Each user-view page binds to exactly one bundled endpoint that returns
*everything* the page needs in a single round trip. The frontend
renders cards directly off these payloads — no orchestration.

Design principle: **one page, one fetch, one above-the-fold primary
action.** The ``primary_action`` field on every bundle names what that
above-the-fold CTA is — frontend never invents one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    RiskLevel,
)
from schemas.synthetic.weather_v2_schema import WeatherMoodContext
from schemas.synthetic.trajectory_alert_schema import TrajectoryAlertStatus


# ── Shared pieces ──────────────────────────────────────────────────────────


class PrimaryAction(BaseModel):
    """The single call-to-action above the fold for a page."""

    label: str
    endpoint: str
    method: str = "POST"
    icon_hint: str = "arrow-right"


class RenderHint(BaseModel):
    """Reusable card-render-hint bundle, mirroring trajectory alert UI tokens."""

    severity_color: str
    icon_hint: str
    microcopy: str


# ── 1. My Summary (dashboard) bundle ───────────────────────────────────────


class MoodMetric(BaseModel):
    sleep_hours: float
    sleep_quality_pct: int
    heart_rate_bpm: int
    stress_pct: int


class MySummaryBundle(BaseModel):
    page_title: str = "My Summary"
    page_subtitle: str = "How you're doing today, in plain language."
    primary_action: PrimaryAction

    greeting: str
    risk_level: RiskLevel
    risk_confidence: float
    risk_render: RenderHint

    seven_day_metrics: MoodMetric

    weather_context: WeatherMoodContext
    trajectory_alert: TrajectoryAlertStatus

    affirmation: Optional[str] = None
    quote: Optional[Dict[str, str]] = None

    next_action_card: RenderHint
    computed_at: datetime
    source: str = "live"


# ── 2. See My Future (renamed What-If Simulator) bundle ────────────────────


class FutureScenario(BaseModel):
    label: str = Field(..., description="'Continue current plan' | 'CBT' | 'Exercise' …")
    intervention_type: InterventionType
    intensity: float
    projected_vitals: List[DayVitals]
    projected_risk_level: RiskLevel
    projected_high_risk_probability: float
    delta_high_risk_probability: float = Field(
        ...,
        description="Negative = improvement vs current.",
    )
    narrative: str = Field(
        ...,
        description="3-4 sentence Day-7 reflection (Future-Self engine).",
    )
    narrative_source: str
    render: RenderHint
    try_this_endpoint: str = Field(
        ...,
        description="Endpoint the 'Try This Plan' button should hit to "
                    "pre-fill the AI Recommendation page with this "
                    "intervention vector.",
    )


class SeeMyFutureBundle(BaseModel):
    page_title: str = "See My Future"
    page_subtitle: str = "What the next week could look like — choose a path."
    primary_action: PrimaryAction

    current_risk_level: RiskLevel
    current_high_risk_probability: float
    starting_vitals: List[DayVitals]

    weather_prefill: WeatherMoodContext = Field(
        ...,
        description="Pre-loaded from Open-Meteo so the user lands on a "
                    "fully-populated simulation with zero setup.",
    )
    scenarios: List[FutureScenario]

    advisory: str
    computed_at: datetime
    source: str = "live"


# ── 3. AI Recommendation (NBA + Compare + Prescription merged) bundle ──────


class EvidenceCard(BaseModel):
    pmid: Optional[str] = None
    title: str
    snippet: str
    pubmed_url: Optional[str] = None


class RecommendationCard(BaseModel):
    rank: int
    label: str = Field(..., description="Human-language name (e.g. 'Your Personalized Plan').")
    intervention_type: InterventionType
    intensity: float
    confidence: float
    delta_high_risk_probability: float
    ease_score: float
    why_this: str = Field(..., description="One sentence: why this for you, now.")
    narrative_snippet: str = Field(
        ..., description="Future-Self narrative, lightly trimmed.",
    )
    evidence: List[EvidenceCard] = Field(
        default_factory=list,
        description="0–3 PubMed cards for trust-building.",
    )
    render: RenderHint


class AIRecommendationBundle(BaseModel):
    page_title: str = "AI Recommendation"
    page_subtitle: str = (
        "Three plans, ranked for you — pick the one that fits this week."
    )
    primary_action: PrimaryAction

    pre_filled_intervention: Optional[Dict[str, Any]] = Field(
        None,
        description="Set when the user arrived via 'Try This Plan' from "
                    "See My Future; the page can highlight the matching "
                    "card.",
    )
    cards: List[RecommendationCard] = Field(..., min_length=2, max_length=3)

    accept_endpoint: str = "/api/v1/feedback/intervention"
    decline_endpoint: str = "/api/v1/feedback/intervention"
    computed_at: datetime
    source: str = "live"


# ── 4. Digital Twin bundle ─────────────────────────────────────────────────


class OnboardingStep(BaseModel):
    title: str
    body: str
    illustration_id: str = Field(
        ..., description="Stable id (lucide icon name OR named SVG) for "
                         "the frontend to look up the illustration.",
    )


class DigitalTwinBundle(BaseModel):
    page_title: str = "Digital Twin"
    page_subtitle: str = (
        "We create a private AI version of you, so we can answer "
        "'what would happen if…' without using your real data."
    )
    primary_action: PrimaryAction

    onboarding: List[OnboardingStep] = Field(
        ...,
        description="Three steps for the first-time guided tour. Frontend "
                    "should only render this when the user has not "
                    "completed onboarding (per local-storage flag).",
    )
    twin_preview: Optional[Dict[str, Any]] = Field(
        None,
        description="A sample synthetic profile generated *for the demo* "
                    "(never the real user's data).",
    )
    privacy_promises: List[str]
    computed_at: datetime
    source: str = "live"


# ── 5. Understand My Risk (simplified XAI) bundle ──────────────────────────


class XAIFactor(BaseModel):
    feature: str
    plain_english: str
    direction: str = Field(..., description="'increases' | 'decreases'")
    magnitude_pct: int = Field(..., ge=0, le=100)
    icon_hint: str
    color: str


class UnderstandMyRiskBundle(BaseModel):
    page_title: str = "Understand My Risk"
    page_subtitle: str = "What's pushing your risk up, and what's bringing it down."
    primary_action: PrimaryAction

    risk_level: RiskLevel
    risk_confidence: float
    risk_render: RenderHint

    plain_english_summary: str = Field(
        ...,
        description="One sentence — the default view. e.g. 'Your sleep "
                    "schedule is the biggest factor in your risk level.'",
    )
    top_factors: List[XAIFactor] = Field(
        ..., min_length=1, max_length=5,
        description="Up to five plain-English factors with direction + "
                    "magnitude. Colour and icon are render hints.",
    )

    advanced_available: bool = True
    advanced_endpoint: str = "/api/v1/xai/explain_risk"
    advanced_label: str = "Show technical breakdown (SHAP waterfall)"

    computed_at: datetime
    source: str = "live"


# ── 6. Guided Therapy Session bundle (lightweight; full flow lives at /therapy) ──


class GuidedTherapyEntryBundle(BaseModel):
    page_title: str = "Guided Therapy Session"
    page_subtitle: str = (
        "A 7-phase, 15–25 minute structured conversation. You're in control "
        "of the pace."
    )
    primary_action: PrimaryAction

    phases: List[Dict[str, str]] = Field(
        ...,
        description="Phase id + label + estimated minutes — for the "
                    "progress strip.",
    )
    safety_promise: str
    last_session_summary: Optional[Dict[str, Any]] = None
    computed_at: datetime
    source: str = "live"
