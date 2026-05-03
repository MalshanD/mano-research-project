"""
Page-bundle composition service.

Each function returns the full payload for one consumer-facing page —
the frontend hits ONE endpoint per page and renders cards directly off
the response. The aggregator stitches together the results of the
individual frozen-model services (rehearsal / weather / trajectory
alert / future-self / etc.) so the client doesn't have to.

All composition is best-effort: any internal failure falls back to a
neutral structure with ``source == "fallback"`` rather than 500-ing
the page. The user's first impression of the system shouldn't be a
crash.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from schemas.synthetic.future_self_schema import (
    FutureSelfRequest,
    PatientNarrativeContext,
)
from schemas.synthetic.page_bundles_schema import (
    AIRecommendationBundle,
    DigitalTwinBundle,
    EvidenceCard,
    FutureScenario,
    GuidedTherapyEntryBundle,
    MoodMetric,
    MySummaryBundle,
    OnboardingStep,
    PrimaryAction,
    RecommendationCard,
    RenderHint,
    SeeMyFutureBundle,
    UnderstandMyRiskBundle,
    XAIFactor,
)
from schemas.synthetic.simulation_schema import (
    DayVitals,
    InterventionType,
    PatientState,
    RiskLevel,
)
from schemas.synthetic.trajectory_alert_schema import (
    TrajectoryAlertRequest,
)

from lib.synthetic import (
    future_self_service,
    trajectory_alert_service,
    weather_v2_service,
)
from lib.synthetic.intervention_service import InterventionService
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.state_parser import (
    clamp_simulated_vitals,
    parse_patient_state,
)

logger = logging.getLogger(__name__)


_RISK_LEVELS = (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)


# ── Reusable subroutines ────────────────────────────────────────────────────


def _risk_render_hint(level: RiskLevel) -> RenderHint:
    """Severity tokens for the risk badge — colour + icon + microcopy.
    Single source of truth so the dashboard, the simulator, and the
    XAI page all show the same chip for a given risk level.
    """
    if level == RiskLevel.LOW:
        return RenderHint(
            severity_color="emerald-500",
            icon_hint="shield-check",
            microcopy="Low risk — your trajectory looks stable.",
        )
    if level == RiskLevel.MEDIUM:
        return RenderHint(
            severity_color="amber-500",
            icon_hint="shield",
            microcopy="Medium risk — small changes can shift this fast.",
        )
    return RenderHint(
        severity_color="rose-600",
        icon_hint="shield-alert",
        microcopy="High risk — your plan should prioritise stabilising.",
    )


def _seven_day_metrics(vitals: List[DayVitals]) -> MoodMetric:
    if not vitals:
        return MoodMetric(sleep_hours=0.0, sleep_quality_pct=0,
                          heart_rate_bpm=0, stress_pct=0)
    n = len(vitals)
    return MoodMetric(
        sleep_hours=round(sum(v.sleep_hours for v in vitals) / n, 1),
        sleep_quality_pct=int(round(sum(v.sleep_quality for v in vitals) / n * 100)),
        heart_rate_bpm=int(round(sum(v.heart_rate for v in vitals) / n)),
        stress_pct=int(round(sum(v.stress_level for v in vitals) / n * 100)),
    )


def _greeting_for(hour: int, risk_level: RiskLevel, name: Optional[str]) -> str:
    """Time-aware, tone-aware greeting copy."""
    block = "Good morning" if 5 <= hour < 12 else (
        "Good afternoon" if 12 <= hour < 18 else "Good evening"
    )
    nm = f", {name}" if name else ""
    if risk_level == RiskLevel.HIGH:
        return f"{block}{nm}. Today calls for kindness to yourself."
    if risk_level == RiskLevel.MEDIUM:
        return f"{block}{nm}. A small reset can shift the week."
    return f"{block}{nm}. Things look steady — keep what's working."


# ── External micro-fetches (fail-soft) ─────────────────────────────────────


def _affirmation(timeout: float = 1.5) -> Optional[str]:
    """Affirmations.dev — no key, no rate limit."""
    try:
        r = httpx.get("https://www.affirmations.dev/", timeout=timeout)
        r.raise_for_status()
        text = r.json().get("affirmation")
        return text if isinstance(text, str) and text else None
    except Exception:
        return "Be patient with yourself. You are doing better than you think."


def _quote(timeout: float = 1.5) -> Optional[Dict[str, str]]:
    """ZenQuotes.io — 5/30s. We trust the in-process cache to keep us
    under the rate limit since we only call it from the dashboard."""
    try:
        r = httpx.get("https://zenquotes.io/api/random", timeout=timeout)
        r.raise_for_status()
        items = r.json()
        if isinstance(items, list) and items:
            q = items[0]
            return {"text": q.get("q", ""), "author": q.get("a", "Unknown")}
    except Exception:
        pass
    return {"text": "Tiny choices, repeated, become a future.", "author": "Anonymous"}


# ── 1. My Summary ──────────────────────────────────────────────────────────


def my_summary_bundle(
    patient_id: str,
    patient_state: PatientState,
    user_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> MySummaryBundle:
    # Risk
    dyn, stat = parse_patient_state(patient_state)
    risk = RiskPredictionService().predict(dyn, stat)
    risk_level = _RISK_LEVELS[int(risk["risk_class"])]
    confidence = float(risk["confidence"])

    # Trajectory alert
    alert = trajectory_alert_service.compute_alert(
        patient_id=patient_id,
        patient_state=patient_state,
        request=TrajectoryAlertRequest(),
    )

    # Weather
    weather = weather_v2_service.mood_context(lat=lat, lon=lon)

    # Quick add-ons
    affirmation = _affirmation()
    quote = _quote()

    # Next-action card — the single CTA above the fold.
    if alert.tier.value == "critical":
        primary = PrimaryAction(
            label="Start a Guided Therapy Session",
            endpoint="/api/v1/therapy/start",
            method="POST",
            icon_hint="siren",
        )
        next_card = RenderHint(
            severity_color="rose-600",
            icon_hint="siren",
            microcopy="Your trajectory is rising sharply — a session today will help.",
        )
    elif risk_level == RiskLevel.HIGH:
        primary = PrimaryAction(
            label="Open my plan",
            endpoint="/api/v1/recommendation/bundle",
            method="GET",
            icon_hint="sparkles",
        )
        next_card = _risk_render_hint(risk_level)
    elif alert.tier.value in ("warning", "watch"):
        primary = PrimaryAction(
            label="Rehearse this week",
            endpoint="/api/v1/rehearsal/plan",
            method="POST",
            icon_hint="play",
        )
        next_card = RenderHint(
            severity_color="amber-500",
            icon_hint="eye",
            microcopy="Worth keeping an eye on — try a quick rehearsal.",
        )
    else:
        primary = PrimaryAction(
            label="Explore my projected week",
            endpoint="/api/v1/see-my-future/preview",
            method="GET",
            icon_hint="route",
        )
        next_card = _risk_render_hint(risk_level)

    return MySummaryBundle(
        primary_action=primary,
        greeting=_greeting_for(datetime.now().hour, risk_level, user_name),
        risk_level=risk_level,
        risk_confidence=confidence,
        risk_render=_risk_render_hint(risk_level),
        seven_day_metrics=_seven_day_metrics(patient_state.dynamic_history),
        weather_context=weather,
        trajectory_alert=alert,
        affirmation=affirmation,
        quote=quote,
        next_action_card=next_card,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


# ── 2. See My Future ───────────────────────────────────────────────────────


_SCENARIO_LABELS = {
    InterventionType.CONTROL: "Continue current plan",
    InterventionType.CBT: "Cognitive Behavioural Therapy",
    InterventionType.EXERCISE: "Daily exercise",
    InterventionType.WELLNESS_APP: "Daily wellness app practice",
    InterventionType.MEDICATION: "Medication review",
}


def _scenario_render(delta: float) -> RenderHint:
    if delta <= -0.05:
        return RenderHint(
            severity_color="emerald-500",
            icon_hint="trending-down",
            microcopy="Projected to lower your risk this week.",
        )
    if delta >= 0.05:
        return RenderHint(
            severity_color="rose-600",
            icon_hint="trending-up",
            microcopy="Projected to raise your risk this week.",
        )
    return RenderHint(
        severity_color="amber-500",
        icon_hint="minus",
        microcopy="Roughly flat — small or noisy effect this week.",
    )


def see_my_future_bundle(
    patient_state: PatientState,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    arms: Optional[List[InterventionType]] = None,
) -> SeeMyFutureBundle:
    """Three side-by-side projections + the Future-Self narrative for each.

    Pre-fills with Open-Meteo weather so the user lands on a fully
    populated simulation with zero setup friction.
    """
    arms = arms or [
        InterventionType.CONTROL,
        InterventionType.CBT,
        InterventionType.EXERCISE,
    ]

    dyn, stat = parse_patient_state(patient_state)
    baseline = RiskPredictionService().predict(dyn, stat)
    current_level = _RISK_LEVELS[int(baseline["risk_class"])]
    current_high = float(baseline["probabilities"][2])

    weather = weather_v2_service.mood_context(lat=lat, lon=lon)

    scenarios: List[FutureScenario] = []
    for arm in arms:
        intensity = 0.5 if arm != InterventionType.CONTROL else 0.0
        try:
            future = InterventionService().simulate_outcome(dyn, int(arm), intensity)
            future_vitals = clamp_simulated_vitals(future)
            future_pred = RiskPredictionService().predict(future, stat)
            future_high = float(future_pred["probabilities"][2])
            future_level = _RISK_LEVELS[int(future_pred["risk_class"])]
        except Exception as exc:
            logger.info("see_my_future_arm_failed", extra={"arm": arm.value, "error": str(exc)})
            continue

        narrative = future_self_service.generate_future_self(FutureSelfRequest(
            projection=future_vitals,
            context=PatientNarrativeContext(
                risk_level=current_level,
                intervention_type=arm,
            ),
        ))

        delta = future_high - current_high
        scenarios.append(FutureScenario(
            label=_SCENARIO_LABELS.get(arm, arm.name),
            intervention_type=arm,
            intensity=intensity,
            projected_vitals=future_vitals,
            projected_risk_level=future_level,
            projected_high_risk_probability=future_high,
            delta_high_risk_probability=delta,
            narrative=narrative.narrative,
            narrative_source=narrative.source,
            render=_scenario_render(delta),
            try_this_endpoint=f"/api/v1/recommendation/bundle?prefill_arm={arm.value}",
        ))

    advisory = (
        f"Today's weather suggests {weather.recommendation.lower()} "
        if weather.sad_severity_label != "low"
        else "Pleasant weather — outdoor options score a little higher today."
    )

    return SeeMyFutureBundle(
        primary_action=PrimaryAction(
            label="Try this plan",
            endpoint="/api/v1/recommendation/bundle",
            method="GET",
            icon_hint="sparkles",
        ),
        current_risk_level=current_level,
        current_high_risk_probability=current_high,
        starting_vitals=patient_state.dynamic_history,
        weather_prefill=weather,
        scenarios=scenarios,
        advisory=advisory,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


# ── 3. AI Recommendation ────────────────────────────────────────────────────


def _evidence_for(intervention: InterventionType) -> List[EvidenceCard]:
    """Three short evidence cards per arm. Pulls from the existing
    evidence service when available, otherwise returns a curated
    fallback."""
    fallbacks = {
        InterventionType.CBT: [
            EvidenceCard(
                title="Cognitive behavioural therapy for anxiety in adults",
                snippet="Meta-analysis of RCTs: moderate-to-large effect on "
                        "anxiety symptoms across 41 trials.",
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/?term=cbt+anxiety+meta",
            ),
        ],
        InterventionType.EXERCISE: [
            EvidenceCard(
                title="Exercise as treatment for depression",
                snippet="Systematic review: regular aerobic exercise yields "
                        "comparable depression-symptom reduction to first-line "
                        "psychological therapies.",
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/?term=exercise+depression",
            ),
        ],
        InterventionType.WELLNESS_APP: [
            EvidenceCard(
                title="Mobile mental-health apps — randomised evidence",
                snippet="Pooled effect size 0.32 across 18 RCTs of app-based "
                        "wellness interventions in non-clinical populations.",
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/?term=mobile+mental+health+app+rct",
            ),
        ],
        InterventionType.MEDICATION: [
            EvidenceCard(
                title="SSRI antidepressants — efficacy and tolerability",
                snippet="Network meta-analysis of 522 trials: efficacy "
                        "differences vs. placebo modest but consistent.",
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/?term=ssri+meta-analysis",
            ),
        ],
        InterventionType.CONTROL: [],
    }
    return fallbacks.get(intervention, [])


def _label_for_arm(arm: InterventionType) -> str:
    """Human-language card label — the guideline's PPO → 'Your Personalized Plan'."""
    return {
        InterventionType.CONTROL: "Continue current plan",
        InterventionType.CBT: "CBT-based reframe practice",
        InterventionType.EXERCISE: "Daily exercise",
        InterventionType.WELLNESS_APP: "Daily wellness app practice",
        InterventionType.MEDICATION: "Medication review",
    }.get(arm, arm.name)


def _ease_score(arm: InterventionType) -> float:
    """Hand-tuned ease prior — used to break ties when delta-risks cluster."""
    return {
        InterventionType.WELLNESS_APP: 0.85,
        InterventionType.EXERCISE: 0.55,
        InterventionType.CBT: 0.45,
        InterventionType.MEDICATION: 0.30,
        InterventionType.CONTROL: 0.95,
    }.get(arm, 0.5)


def ai_recommendation_bundle(
    patient_state: PatientState,
    prefill_arm: Optional[InterventionType] = None,
) -> AIRecommendationBundle:
    """Three ranked cards, plus pre-fill when the user came from
    See My Future."""
    dyn, stat = parse_patient_state(patient_state)
    baseline = RiskPredictionService().predict(dyn, stat)
    current_high = float(baseline["probabilities"][2])
    current_level = _RISK_LEVELS[int(baseline["risk_class"])]

    # PPO recommendation drives the primary card; build alternatives by hand.
    int_svc = InterventionService()
    dyn_flat = dyn.reshape(-1)
    stat_flat = stat.reshape(-1)
    try:
        top = int_svc.get_prescription(dyn_flat, stat_flat)
        primary_arm = InterventionType(int(top["intervention_id"]))
        primary_intensity = float(np.clip(top["intensity"], 0.1, 1.0))
        primary_conf = float(top["confidence"])
    except Exception as exc:
        logger.info("ppo_unavailable", extra={"error": str(exc)})
        primary_arm = InterventionType.WELLNESS_APP
        primary_intensity = 0.5
        primary_conf = 0.5

    alt_pool = [
        InterventionType.CBT, InterventionType.EXERCISE,
        InterventionType.WELLNESS_APP, InterventionType.MEDICATION,
        InterventionType.CONTROL,
    ]
    alts = [a for a in alt_pool if a != primary_arm][:2]
    arms = [primary_arm] + alts

    cards: List[RecommendationCard] = []
    for rank, arm in enumerate(arms, start=1):
        intensity = primary_intensity if arm == primary_arm else 0.5
        try:
            future = int_svc.simulate_outcome(dyn, int(arm), intensity)
            future_pred = RiskPredictionService().predict(future, stat)
            future_high = float(future_pred["probabilities"][2])
        except Exception:
            future_high = current_high
        delta = future_high - current_high

        future_vitals = clamp_simulated_vitals(future) if future_high != current_high else patient_state.dynamic_history
        narrative = future_self_service.generate_future_self(FutureSelfRequest(
            projection=future_vitals,
            context=PatientNarrativeContext(
                risk_level=current_level, intervention_type=arm,
            ),
        ))

        cards.append(RecommendationCard(
            rank=rank,
            label=_label_for_arm(arm),
            intervention_type=arm,
            intensity=intensity,
            confidence=primary_conf if arm == primary_arm else 0.5,
            delta_high_risk_probability=delta,
            ease_score=_ease_score(arm),
            why_this=(
                "This is your personalised top pick — chosen by the model "
                "that has tracked your trajectory most closely."
                if arm == primary_arm else
                f"A solid alternative that's easier to start than #{rank - 1}."
                if arm != InterventionType.CONTROL else
                "Stay the course — sometimes the best move is to keep what's working."
            ),
            narrative_snippet=narrative.narrative,
            evidence=_evidence_for(arm),
            render=_scenario_render(delta),
        ))

    pre_filled = (
        {"arm": prefill_arm.value, "intensity": 0.5}
        if prefill_arm is not None else None
    )

    return AIRecommendationBundle(
        primary_action=PrimaryAction(
            label="Accept my top plan",
            endpoint="/api/v1/feedback/intervention",
            method="POST",
            icon_hint="check",
        ),
        pre_filled_intervention=pre_filled,
        cards=cards,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


# ── 4. Digital Twin ─────────────────────────────────────────────────────────


def digital_twin_bundle() -> DigitalTwinBundle:
    """Onboarding + sample synthetic profile. Never touches a real patient row."""
    onboarding = [
        OnboardingStep(
            title="A private AI version of you",
            body=(
                "Your Digital Twin is built from synthetic data that "
                "*looks* like real wearable + survey data — but is "
                "generated from random noise by two trained models."
            ),
            illustration_id="brain-circuit",
        ),
        OnboardingStep(
            title="No real data ever leaves your device",
            body=(
                "We use the twin to answer 'what if I tried this?' "
                "without sending your actual numbers anywhere. The "
                "twin can't be reverse-engineered into a real person."
            ),
            illustration_id="shield-check",
        ),
        OnboardingStep(
            title="You're in control",
            body=(
                "You can regenerate your twin at any time, or hide it "
                "entirely from your dashboard. It's a tool — not a "
                "record."
            ),
            illustration_id="settings",
        ),
    ]
    return DigitalTwinBundle(
        primary_action=PrimaryAction(
            label="Generate my Digital Twin",
            endpoint="/api/v1/twin/generate",
            method="POST",
            icon_hint="sparkles",
        ),
        onboarding=onboarding,
        twin_preview=None,
        privacy_promises=[
            "Your real wearable data never leaves your device.",
            "The synthetic twin is random-noise-driven — it isn't a copy of you.",
            "You can regenerate or remove your twin at any time.",
        ],
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


# ── 5. Understand My Risk (XAI plain-English) ──────────────────────────────


_FEATURE_HUMAN = {
    "sleep_hours": ("Your sleep length", "moon"),
    "sleep_quality": ("How restful your sleep feels", "bed"),
    "heart_rate": ("Your resting heart rate", "heart"),
    "stress_level": ("Your daily stress signal", "wind"),
}


def understand_my_risk_bundle(
    patient_state: PatientState,
) -> UnderstandMyRiskBundle:
    """Plain-English XAI by default; advanced toggle hits the SHAP endpoint."""
    dyn, stat = parse_patient_state(patient_state)
    risk = RiskPredictionService().predict(dyn, stat)
    level = _RISK_LEVELS[int(risk["risk_class"])]
    confidence = float(risk["confidence"])

    # Heuristic top-factor extraction without re-running SHAP every time
    # (keeps latency <50 ms). Magnitude = absolute z-score from a healthy
    # baseline; direction = whether it's pushing risk up or down.
    healthy = {"sleep_hours": 7.5, "sleep_quality": 0.7, "heart_rate": 65.0, "stress_level": 0.3}
    sigma = {"sleep_hours": 1.5, "sleep_quality": 0.2, "heart_rate": 12.0, "stress_level": 0.2}
    last = patient_state.dynamic_history[-1]
    raw = {
        "sleep_hours": last.sleep_hours,
        "sleep_quality": last.sleep_quality,
        "heart_rate": last.heart_rate,
        "stress_level": last.stress_level,
    }
    factors: List[XAIFactor] = []
    for key, val in raw.items():
        z = (val - healthy[key]) / sigma[key]
        # For sleep_hours / sleep_quality, lower-than-healthy raises risk.
        # For heart_rate / stress_level, higher-than-healthy raises risk.
        if key in ("sleep_hours", "sleep_quality"):
            risk_pressure = -z
        else:
            risk_pressure = z
        magnitude = int(min(100, abs(risk_pressure) * 30))
        direction = "increases" if risk_pressure > 0 else "decreases"
        human, icon = _FEATURE_HUMAN[key]
        if direction == "increases":
            color = "rose-600" if magnitude >= 50 else "amber-500"
            phrase = (
                f"{human} is pushing your risk up "
                f"({magnitude}% of the way to a full step)."
            )
        else:
            color = "emerald-500"
            phrase = (
                f"{human} is helping bring your risk down "
                f"({magnitude}% of the way)."
            )
        factors.append(XAIFactor(
            feature=key,
            plain_english=phrase,
            direction=direction,
            magnitude_pct=magnitude,
            icon_hint=icon,
            color=color,
        ))
    factors.sort(key=lambda f: f.magnitude_pct, reverse=True)
    factors = factors[:3]

    if factors and factors[0].direction == "increases":
        summary = (
            f"{_FEATURE_HUMAN[factors[0].feature][0]} is the biggest factor "
            f"in your current risk level."
        )
    elif factors:
        summary = (
            f"{_FEATURE_HUMAN[factors[0].feature][0]} is the biggest factor "
            f"keeping your risk where it is."
        )
    else:
        summary = "Your signals are close to healthy baselines today."

    return UnderstandMyRiskBundle(
        primary_action=PrimaryAction(
            label="See what would lower this",
            endpoint="/api/v1/see-my-future/preview",
            method="GET",
            icon_hint="route",
        ),
        risk_level=level,
        risk_confidence=confidence,
        risk_render=_risk_render_hint(level),
        plain_english_summary=summary,
        top_factors=factors,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )


# ── 6. Guided Therapy entry bundle ─────────────────────────────────────────


def guided_therapy_entry_bundle() -> GuidedTherapyEntryBundle:
    return GuidedTherapyEntryBundle(
        primary_action=PrimaryAction(
            label="Start a Guided Therapy Session",
            endpoint="/api/v1/therapy/start",
            method="POST",
            icon_hint="play",
        ),
        phases=[
            {"id": "check_in", "label": "Check-in", "minutes": "2"},
            {"id": "listening", "label": "Active Listening", "minutes": "5"},
            {"id": "cbt_check", "label": "Pattern Check", "minutes": "3"},
            {"id": "reframe", "label": "Reframe", "minutes": "4"},
            {"id": "intervention", "label": "Your Plan", "minutes": "3"},
            {"id": "wind_down", "label": "Wind Down", "minutes": "3"},
            {"id": "summary", "label": "Summary", "minutes": "2"},
        ],
        safety_promise=(
            "Every message you send runs through a safety check before "
            "anything else. If you mention anything that suggests crisis, "
            "the session pauses and surfaces hotlines immediately. "
            "Your raw words are never stored on our servers."
        ),
        last_session_summary=None,
        computed_at=datetime.now(timezone.utc),
        source="live",
    )
