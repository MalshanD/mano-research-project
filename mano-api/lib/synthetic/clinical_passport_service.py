"""
Clinical Passport PDF generator.

Pipeline
--------
1. Accept a pre-composed ``ClinicalPassportRequest`` (the passport is a
   *pass-through* renderer — callers upstream stitch live data).
2. Compose a ReportLab ``SimpleDocTemplate`` in-memory, one section per
   payload block that is populated. Missing blocks are silently omitted
   and recorded as a warning so the response surfaces what was skipped.
3. Write the PDF to disk at ``<passport_dir>/<passport_id>.pdf``. The
   directory is created on first use.
4. Publish ``Topics.PASSPORT_RENDERED`` with the identifier + path so
   downstream subscribers (audit log, email digest, etc.) can react.

Design notes
~~~~~~~~~~~~
* We deliberately avoid Unicode sub/superscript glyphs — ReportLab's
  built-in fonts don't contain them. The skill guide in ``skills/pdf``
  flags this as a frequent gotcha.
* Every table uses fixed column widths in points so the layout is stable
  regardless of printer. Page is US Letter to match the NHS / US shared
  clinical workflow.
* The generator is **idempotent for a given payload hash** — the same
  ``patient_id`` + content will land in a new file each call (we include
  a UUID), because passports are audit artefacts: never overwrite.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from lib.infra.event_bus import Topics, publish
from schemas.synthetic.clinical_passport_schema import (
    ClinicalPassportRequest,
    ClinicalPassportResponse,
)

logger = logging.getLogger(__name__)


# ─── Paths ────────────────────────────────────────────────────────────────

def _passport_dir() -> Path:
    """Where rendered passports live on disk.

    Overrideable via ``MANO_PASSPORT_DIR``. Default is ``data/passports``
    under the process cwd — that keeps the default artefact path predictable
    without requiring config.py changes.
    """
    raw = os.environ.get("MANO_PASSPORT_DIR") or os.path.join("data", "passports")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _public_url_for(filename: str) -> str:
    """URL the frontend uses to fetch the PDF back.

    We expose passports via the router's own ``GET /file/{passport_id}``
    rather than serving the directory statically — that way we can add
    auth / audit logging in one place.
    """
    # The passport_id IS the filename stem — strip the extension.
    stem = Path(filename).stem
    return f"/api/v1/passport/file/{stem}"


# ─── Default copy ─────────────────────────────────────────────────────────

_DEFAULT_DISCLAIMER = (
    "This passport is an algorithmically-generated decision-support "
    "summary from the MANO platform. It is NOT a diagnosis and must be "
    "reviewed by a qualified clinician before any care decision. Frozen "
    "models: LSTM risk classifier, Seq2Seq + Attention intervention "
    "simulator, PPO actor-critic policy, CTGAN / TimeGAN synthesisers."
)


_RISK_COLOUR = {
    "low": colors.HexColor("#1f7a2a"),
    "medium": colors.HexColor("#c77a00"),
    "high": colors.HexColor("#b1272e"),
}


# ─── Styles ───────────────────────────────────────────────────────────────

def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PassportTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1a3a5c"),
        alignment=TA_LEFT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="PassportSectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=10,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="PassportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=13,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="PassportSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#555555"),
    ))
    return styles


# ─── Section builders ─────────────────────────────────────────────────────

def _header_story(
    styles, request: ClinicalPassportRequest, passport_id: str, generated_at: datetime,
) -> List:
    story: List = []
    title = request.patient_display_name or f"Patient {request.patient_id}"
    story.append(Paragraph(f"MANO Clinical Passport — {title}", styles["PassportTitle"]))
    meta = (
        f"Passport ID: <b>{passport_id}</b> &nbsp;&nbsp; "
        f"Patient ID: <b>{request.patient_id}</b><br/>"
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    if request.generated_for:
        meta += f" &nbsp;&nbsp; For: {request.generated_for}"
    story.append(Paragraph(meta, styles["PassportSmall"]))
    story.append(Spacer(1, 8))
    return story


def _risk_section(styles, request: ClinicalPassportRequest) -> List:
    story: List = []
    story.append(Paragraph("Risk snapshot", styles["PassportSectionHeader"]))
    r = request.risk_snapshot
    colour = _RISK_COLOUR.get(r.risk_level, colors.black)
    headline = Paragraph(
        f"<b>Current classification: <font color='{colour.hexval()}'>"
        f"{r.risk_level.upper()}</font></b>",
        styles["PassportBody"],
    )
    story.append(headline)

    rows = [
        ["Axis", "Value"],
        ["High-risk probability", f"{r.high_risk_probability:.1%}"],
        ["Medium-risk probability", f"{r.medium_risk_probability:.1%}"],
        ["Low-risk probability", f"{r.low_risk_probability:.1%}"],
    ]
    if r.confidence is not None:
        rows.append(["Classifier confidence", f"{r.confidence:.1%}"])
    if r.classifier_uncertainty is not None:
        rows.append(["MC-Dropout uncertainty", f"{r.classifier_uncertainty:.1%}"])

    table = Table(rows, colWidths=[2.5 * inch, 2.0 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    return story


def _trajectory_section(styles, request: ClinicalPassportRequest) -> List:
    if not request.trajectory:
        return []
    story: List = []
    story.append(Paragraph("Forecast trajectory", styles["PassportSectionHeader"]))
    rows = [["Day", "High-risk p", "95% CI lower", "95% CI upper"]]
    for point in request.trajectory:
        rows.append([
            str(point.day),
            f"{point.mean_high_risk_probability:.1%}",
            f"{point.lower_ci:.1%}" if point.lower_ci is not None else "—",
            f"{point.upper_ci:.1%}" if point.upper_ci is not None else "—",
        ])
    table = Table(rows, colWidths=[0.8 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    return story


def _interventions_section(styles, request: ClinicalPassportRequest) -> List:
    if not request.ranked_interventions:
        return []
    story: List = []
    story.append(Paragraph("Recommended interventions (PPO reranker)", styles["PassportSectionHeader"]))

    if request.reranker_weights:
        w = request.reranker_weights
        weight_str = (
            f"Blend: PPO {w.w_ppo_policy:.0%} / sim risk {w.w_simulator_risk_reduction:.0%} / "
            f"adherence {w.w_adherence_prior:.0%} / care-phase {w.w_care_phase_prior:.0%} / "
            f"preference {w.w_patient_preference:.0%}"
        )
        story.append(Paragraph(weight_str, styles["PassportSmall"]))
        story.append(Spacer(1, 4))

    rows = [["Rank", "Intervention", "Final score", "Raw RR", "Why"]]
    for cand in request.ranked_interventions:
        rows.append([
            str(cand.rank),
            cand.intervention_name,
            f"{cand.final_score:.3f}",
            f"{cand.raw_risk_reduction:+.3f}",
            Paragraph(cand.explanation, styles["PassportSmall"]),
        ])
    table = Table(
        rows,
        colWidths=[0.5 * inch, 1.4 * inch, 0.9 * inch, 0.8 * inch, 3.1 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    return story


def _care_path_section(styles, request: ClinicalPassportRequest) -> List:
    if request.care_path is None:
        return []
    cp = request.care_path
    story: List = []
    story.append(Paragraph("Care-path phase", styles["PassportSectionHeader"]))
    tones = ", ".join(cp.recommended_intervention_tones) if cp.recommended_intervention_tones else "—"
    started = cp.phase_started_at.strftime("%Y-%m-%d") if cp.phase_started_at else "—"
    body = (
        f"<b>Current phase:</b> {cp.phase.upper()} &nbsp;&nbsp; "
        f"<b>Started:</b> {started} &nbsp;&nbsp; "
        f"<b>Review cadence:</b> every {cp.review_cadence_days} days<br/>"
        f"<b>Recommended tones:</b> {tones}"
    )
    story.append(Paragraph(body, styles["PassportBody"]))
    if cp.phase_guidance:
        story.append(Paragraph(cp.phase_guidance, styles["PassportBody"]))
    story.append(Spacer(1, 6))
    return story


def _narrative_section(styles, request: ClinicalPassportRequest) -> List:
    if not request.narrative_paragraph:
        return []
    story: List = []
    story.append(Paragraph("Future-self narrative", styles["PassportSectionHeader"]))
    # Escape reportlab markup-sensitive characters minimally.
    safe = (
        request.narrative_paragraph
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    story.append(Paragraph(safe, styles["PassportBody"]))
    story.append(Spacer(1, 6))
    return story


def _evidence_section(styles, request: ClinicalPassportRequest) -> List:
    if not request.evidence:
        return []
    story: List = []
    story.append(Paragraph("Evidence citations", styles["PassportSectionHeader"]))
    for i, item in enumerate(request.evidence, start=1):
        bits = [f"<b>{i}. {item.title}</b>"]
        meta = []
        if item.source:
            meta.append(item.source)
        if item.year:
            meta.append(str(item.year))
        if meta:
            bits.append("(" + ", ".join(meta) + ")")
        line = " ".join(bits)
        if item.url:
            line += f"<br/><font color='#1a3a5c'>{item.url}</font>"
        if item.summary:
            line += f"<br/>{item.summary}"
        story.append(Paragraph(line, styles["PassportBody"]))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 4))
    return story


def _safety_section(styles, request: ClinicalPassportRequest) -> List:
    if not request.blocked_interventions and not request.safety_notes:
        return []
    story: List = []
    story.append(Paragraph("Safety notes", styles["PassportSectionHeader"]))
    if request.blocked_interventions:
        story.append(Paragraph(
            f"<b>Blocked interventions:</b> {', '.join(request.blocked_interventions)}",
            styles["PassportBody"],
        ))
    for note in request.safety_notes:
        story.append(Paragraph(f"• {note}", styles["PassportBody"]))
    story.append(Spacer(1, 6))
    return story


def _footer_story(styles, request: ClinicalPassportRequest) -> List:
    story: List = []
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        request.disclaimer or _DEFAULT_DISCLAIMER,
        styles["PassportSmall"],
    ))
    return story


# ─── Renderer ─────────────────────────────────────────────────────────────

def _render_pdf(
    request: ClinicalPassportRequest, output_path: Path, passport_id: str, generated_at: datetime,
) -> Tuple[List[str], List[str]]:
    """Build the PDF on disk. Returns (sections_included, warnings)."""
    styles = _styles()
    story: List = []
    sections: List[str] = []
    warnings: List[str] = []

    story += _header_story(styles, request, passport_id, generated_at)
    story += _risk_section(styles, request)
    sections.append("risk_snapshot")

    traj = _trajectory_section(styles, request)
    if traj:
        story += traj
        sections.append("trajectory")
    else:
        warnings.append("No trajectory points supplied; section omitted.")

    cp = _care_path_section(styles, request)
    if cp:
        story += cp
        sections.append("care_path")
    else:
        warnings.append("No care-path state supplied; section omitted.")

    inter = _interventions_section(styles, request)
    if inter:
        story += inter
        sections.append("ranked_interventions")
    else:
        warnings.append("No ranked interventions supplied; section omitted.")

    narr = _narrative_section(styles, request)
    if narr:
        story += narr
        sections.append("narrative")

    ev = _evidence_section(styles, request)
    if ev:
        story += ev
        sections.append("evidence")

    safety = _safety_section(styles, request)
    if safety:
        story += safety
        sections.append("safety_notes")

    story += _footer_story(styles, request)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"MANO Clinical Passport — {request.patient_id}",
        author="MANO Platform",
        subject="Clinical decision-support passport",
    )
    doc.build(story)
    return sections, warnings


# ─── Public entrypoint ───────────────────────────────────────────────────

async def generate_passport(request: ClinicalPassportRequest) -> ClinicalPassportResponse:
    passport_id = uuid.uuid4().hex[:16]
    generated_at = datetime.now(timezone.utc)
    out_dir = _passport_dir()
    out_path = out_dir / f"{passport_id}.pdf"

    # Render in a worker thread — reportlab is sync I/O.
    loop = asyncio.get_event_loop()
    sections, warnings = await loop.run_in_executor(
        None, _render_pdf, request, out_path, passport_id, generated_at,
    )

    size_bytes = out_path.stat().st_size if out_path.exists() else 0

    response = ClinicalPassportResponse(
        passport_id=passport_id,
        generated_at=generated_at,
        patient_id=request.patient_id,
        pdf_path=str(out_path),
        pdf_url=_public_url_for(out_path.name),
        size_bytes=size_bytes,
        sections_included=sections,
        warnings=warnings,
    )

    # Fire the event — downstream can audit-log, email, archive etc.
    try:
        await publish(
            Topics.PASSPORT_RENDERED,
            {
                "passport_id": passport_id,
                "patient_id": request.patient_id,
                "pdf_path": response.pdf_path,
                "pdf_url": response.pdf_url,
                "sections_included": sections,
                "size_bytes": size_bytes,
                "generated_at": generated_at.isoformat(),
            },
        )
    except Exception as exc:  # pragma: no cover — bus is best-effort
        logger.warning("passport_event_publish_failed", extra={"error": str(exc)})

    logger.info(
        "passport_rendered",
        extra={
            "passport_id": passport_id,
            "patient_id": request.patient_id,
            "sections": sections,
            "size_bytes": size_bytes,
        },
    )
    return response


def resolve_passport_path(passport_id: str) -> Path:
    """Look up a previously-rendered passport on disk.

    Raises ``FileNotFoundError`` if the file no longer exists. The router
    uses this to answer ``GET /file/{passport_id}``.
    """
    if not passport_id.isalnum() or not (8 <= len(passport_id) <= 64):
        # Defensive — passport_ids are hex uuids of length 16.
        raise FileNotFoundError(passport_id)
    path = _passport_dir() / f"{passport_id}.pdf"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path
