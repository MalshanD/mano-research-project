"""
NLP Clinical Reports — Router

Auto-generates structured clinical narratives from patient data,
LSTM risk predictions, and PPO intervention recommendations.

APPROACH: Template-based NLP with clinical vocabulary.
- Analyzes patient vitals patterns (7-day trends)
- Runs LSTM risk prediction
- Runs PPO agent for intervention recommendation
- Generates multi-section clinical report

This avoids external LLM API dependency while producing
clinically useful, structured reports. An LLM integration
point is marked for future enhancement.
"""
from fastapi import APIRouter, HTTPException, Depends
import numpy as np
from datetime import datetime
import uuid

# --- Schemas ---
from schemas.synthetic.report_schema import (
    ClinicalReportRequest,
    ClinicalReportResponse,
    ReportSection,
)
from schemas.synthetic.simulation_schema import RiskLevel

# --- Reuse existing helpers ---
from routes.synthetic.simulation_router import parse_patient_state

# --- Services ---
from lib.synthetic.risk_service import RiskPredictionService
from lib.synthetic.intervention_service import InterventionService

from core.logging import get_logger

logger = get_logger("report_router")

router = APIRouter()

RISK_MAP = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}
RISK_NAMES = {0: "Low", 1: "Medium", 2: "High"}
INTERVENTION_NAMES = ["Control", "Wellness App", "CBT", "Exercise", "Medication"]

FEATURE_LABELS = ["Sleep Hours", "Sleep Quality", "Heart Rate", "Stress Level"]


def get_risk_service():
    return RiskPredictionService()


def get_intervention_service():
    return InterventionService()


def analyze_vitals(dynamic_data: np.ndarray) -> dict:
    """Analyze 7-day vital sign patterns."""
    # dynamic_data shape: (1, 7, 4)
    data = dynamic_data[0]  # (7, 4)

    analysis = {}
    for i, label in enumerate(FEATURE_LABELS):
        values = data[:, i]
        mean_val = float(np.mean(values))
        std_val = float(np.std(values))
        trend = float(values[-1] - values[0])  # positive = increasing
        last_val = float(values[-1])

        analysis[label] = {
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
            "trend": round(trend, 2),
            "last": round(last_val, 2),
            "trend_direction": "increasing" if trend > 0.05 else "decreasing" if trend < -0.05 else "stable",
        }

    return analysis


def generate_vitals_narrative(vitals_analysis: dict) -> ReportSection:
    """Generate a clinical narrative about vital signs."""
    lines = []

    sleep_hrs = vitals_analysis["Sleep Hours"]
    sleep_qual = vitals_analysis["Sleep Quality"]
    hr = vitals_analysis["Heart Rate"]
    stress = vitals_analysis["Stress Level"]

    # Sleep assessment
    if sleep_hrs["mean"] < 6:
        lines.append(f"Sleep duration is concerning at {sleep_hrs['mean']:.1f}h average (below recommended 7-9h), "
                     f"with a {sleep_hrs['trend_direction']} trend.")
        severity = "warning"
    elif sleep_hrs["mean"] < 7:
        lines.append(f"Sleep duration is suboptimal at {sleep_hrs['mean']:.1f}h average, "
                     f"trending {sleep_hrs['trend_direction']}.")
        severity = "info"
    else:
        lines.append(f"Sleep duration is adequate at {sleep_hrs['mean']:.1f}h average.")
        severity = "info"

    # Sleep quality
    if sleep_qual["mean"] < 0.5:
        lines.append(f"Sleep quality is poor ({sleep_qual['mean']:.0%}), suggesting fragmented or non-restorative sleep.")
        severity = "warning"
    else:
        lines.append(f"Sleep quality is at {sleep_qual['mean']:.0%}.")

    # Heart rate
    if hr["mean"] > 85:
        lines.append(f"Resting heart rate is elevated at {hr['mean']:.0f} bpm (elevated sympathetic tone).")
        severity = "warning"
    elif hr["mean"] < 60:
        lines.append(f"Resting heart rate is low at {hr['mean']:.0f} bpm (may indicate good fitness or medication effect).")
    else:
        lines.append(f"Heart rate is within normal range at {hr['mean']:.0f} bpm.")

    # Stress
    if stress["mean"] > 0.7:
        lines.append(f"Stress levels are significantly elevated ({stress['mean']:.0%}), "
                     f"{stress['trend_direction']} over the observation period.")
        severity = "critical"
    elif stress["mean"] > 0.5:
        lines.append(f"Moderate stress levels detected ({stress['mean']:.0%}), "
                     f"trending {stress['trend_direction']}.")
    else:
        lines.append(f"Stress levels are within acceptable range ({stress['mean']:.0%}).")

    return ReportSection(
        title="Vital Signs Assessment",
        content=" ".join(lines),
        severity=severity,
    )


def generate_risk_narrative(risk_result: dict) -> ReportSection:
    """Generate a clinical narrative about risk assessment."""
    risk_class = RISK_NAMES[risk_result["risk_class"]]
    probs = risk_result["probabilities"]
    conf = risk_result["confidence"]

    lines = [
        f"The cognitive health risk assessment classifies this patient as {risk_class} risk "
        f"with {conf:.0%} confidence."
    ]

    lines.append(
        f"Probability distribution: Low {probs[0]:.1%}, Medium {probs[1]:.1%}, High {probs[2]:.1%}."
    )

    if risk_result["risk_class"] == 2:
        lines.append("Immediate clinical attention is recommended.")
        severity = "critical"
    elif risk_result["risk_class"] == 1:
        lines.append("Proactive intervention is advised to prevent deterioration.")
        severity = "warning"
    else:
        lines.append("Continue monitoring with current care plan.")
        severity = "info"

    return ReportSection(
        title="Risk Assessment",
        content=" ".join(lines),
        severity=severity,
    )


def generate_recommendation_narrative(
    risk_class: int,
    int_service: InterventionService,
    dyn_np: np.ndarray,
) -> tuple:
    """Generate intervention recommendation narrative. Returns (section, intervention_name)."""
    if risk_class == 0:
        return ReportSection(
            title="Clinical Recommendation",
            content="Patient is at low risk. Maintain current lifestyle patterns and schedule routine follow-up.",
            severity="info",
        ), "Maintain Current Plan"

    # Try PPO recommendation via the intervention service
    try:
        action, intensity = int_service.recommend_intervention(dyn_np)
        int_name = INTERVENTION_NAMES[action] if 0 <= action < len(INTERVENTION_NAMES) else "Unknown"

        if risk_class == 2:
            urgency = "urgently"
            frequency = "with weekly follow-up assessments"
        else:
            urgency = "proactively"
            frequency = "with bi-weekly monitoring"

        content = (
            f"The PPO-based recommendation engine {urgency} recommends "
            f"{int_name} at {intensity:.0%} intensity, {frequency}. "
        )

        if action == 1:  # Wellness App
            content += "Digital therapeutic engagement through guided meditation, sleep hygiene protocols, and cognitive exercises."
        elif action == 2:  # CBT
            content += "Cognitive Behavioral Therapy focusing on stress management, sleep restructuring, and cognitive restructuring techniques."
        elif action == 3:  # Exercise
            content += "Structured physical activity program with progressive intensity, targeting cardiovascular fitness and stress reduction."
        elif action == 4:  # Medication
            content += "Pharmacological intervention may complement behavioral approaches. Consult specialist for prescription."

        return ReportSection(
            title="Clinical Recommendation",
            content=content,
            severity="warning" if risk_class == 1 else "critical",
        ), int_name

    except Exception:
        return ReportSection(
            title="Clinical Recommendation",
            content="Unable to generate automated recommendation. Clinical judgment should guide intervention selection.",
            severity="warning",
        ), "Manual Review Required"


@router.post("/generate", response_model=ClinicalReportResponse)
async def generate_report(
    request: ClinicalReportRequest,
    risk_service: RiskPredictionService = Depends(get_risk_service),
    int_service: InterventionService = Depends(get_intervention_service),
):
    """Generate a structured clinical report from patient data."""
    logger.info("report_generation_start")

    # Step 1: Parse patient state
    dyn_np, stat_np = parse_patient_state(request.patient_state)

    # Step 2: Analyze vitals
    vitals_analysis = analyze_vitals(dyn_np)

    # Step 3: Risk prediction
    risk_result = risk_service.predict(dyn_np, stat_np)
    risk_class = risk_result["risk_class"]

    # Step 4: Generate narrative sections
    sections = []

    # Patient summary section
    patient_id = request.patient_name or "Anonymous Patient"
    demographics = []
    if request.patient_age:
        demographics.append(f"{request.patient_age} years old")
    if request.patient_gender:
        demographics.append(request.patient_gender)

    patient_summary = f"Clinical report for {patient_id}"
    if demographics:
        patient_summary += f" ({', '.join(demographics)})"
    patient_summary += f". Data covers a 7-day observation window ending {datetime.now().strftime('%B %d, %Y')}."

    sections.append(ReportSection(
        title="Patient Overview",
        content=patient_summary,
        severity="info",
    ))

    # Vitals section
    sections.append(generate_vitals_narrative(vitals_analysis))

    # Risk section
    risk_section = generate_risk_narrative(risk_result)
    sections.append(risk_section)

    # Recommendation section (optional)
    recommended_intervention = None
    primary_recommendation = None
    if request.include_recommendations:
        rec_section, int_name = generate_recommendation_narrative(
            risk_class, int_service, dyn_np
        )
        sections.append(rec_section)
        recommended_intervention = int_name
        primary_recommendation = rec_section.content

    # Step 5: Executive summary
    risk_label = RISK_NAMES[risk_class]
    exec_summary = (
        f"Patient assessed at {risk_label} cognitive health risk "
        f"({risk_result['confidence']:.0%} confidence). "
    )

    # Add key concerns
    concerns = []
    if vitals_analysis["Sleep Hours"]["mean"] < 6:
        concerns.append("insufficient sleep")
    if vitals_analysis["Stress Level"]["mean"] > 0.6:
        concerns.append("elevated stress")
    if vitals_analysis["Heart Rate"]["mean"] > 85:
        concerns.append("elevated heart rate")
    if vitals_analysis["Sleep Quality"]["mean"] < 0.5:
        concerns.append("poor sleep quality")

    if concerns:
        exec_summary += f"Key concerns: {', '.join(concerns)}. "
    if recommended_intervention and recommended_intervention != "Maintain Current Plan":
        exec_summary += f"Recommended intervention: {recommended_intervention}."

    # Step 6: Build full report text
    full_text_parts = [
        "=" * 60,
        "COGNITIVE HEALTH CLINICAL REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        f"EXECUTIVE SUMMARY: {exec_summary}",
        "",
    ]

    for section in sections:
        severity_marker = ""
        if section.severity == "critical":
            severity_marker = " [CRITICAL]"
        elif section.severity == "warning":
            severity_marker = " [ATTENTION]"

        full_text_parts.extend([
            f"--- {section.title.upper()}{severity_marker} ---",
            section.content,
            "",
        ])

    full_text_parts.extend([
        "=" * 60,
        "Disclaimer: This report is AI-generated and should be",
        "reviewed by a qualified healthcare professional before",
        "clinical decision-making.",
        "=" * 60,
    ])

    report_id = str(uuid.uuid4())[:8]

    logger.info(
        "report_generated",
        report_id=report_id,
        risk_class=risk_label,
        num_sections=len(sections),
    )

    return ClinicalReportResponse(
        report_id=report_id,
        generated_at=datetime.now().isoformat(),
        patient_identifier=patient_id,
        sections=sections,
        executive_summary=exec_summary,
        risk_classification=risk_label,
        risk_confidence=risk_result["confidence"],
        primary_recommendation=primary_recommendation,
        recommended_intervention=recommended_intervention,
        full_report_text="\n".join(full_text_parts),
    )
