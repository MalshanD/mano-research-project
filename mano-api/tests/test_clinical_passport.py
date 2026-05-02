"""
Clinical Passport PDF generator — end-to-end render test.

Produces a real PDF on a tempdir, verifies magic bytes, section listing,
and the ``/file/{passport_id}`` resolver round-trip.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lib.synthetic.clinical_passport_service import (
    generate_passport,
    resolve_passport_path,
)
from schemas.synthetic.clinical_passport_schema import (
    ClinicalPassportRequest,
    PassportCarePath,
    PassportEvidenceItem,
    PassportRiskSnapshot,
    PassportTrajectoryPoint,
)
from schemas.synthetic.reranker_schema import RerankedCandidate, RerankerWeights


def _sample_request(**overrides) -> ClinicalPassportRequest:
    base = dict(
        patient_id="p-passport-test",
        patient_display_name="Test Patient",
        risk_snapshot=PassportRiskSnapshot(
            risk_level="medium",
            high_risk_probability=0.34,
            medium_risk_probability=0.46,
            low_risk_probability=0.20,
            confidence=0.68,
        ),
    )
    base.update(overrides)
    return ClinicalPassportRequest(**base)


@pytest.mark.asyncio
async def test_minimum_payload_renders(passport_dir):
    req = _sample_request()
    resp = await generate_passport(req)
    assert resp.patient_id == req.patient_id
    assert resp.pdf_path.endswith(".pdf")
    assert resp.size_bytes > 200  # smallest reasonable PDF
    # Risk snapshot is mandatory so should always be present.
    assert "risk_snapshot" in resp.sections_included
    # Downloadable URL uses the router prefix.
    assert resp.pdf_url.startswith("/api/v1/passport/file/")


@pytest.mark.asyncio
async def test_pdf_magic_bytes_are_valid(passport_dir):
    resp = await generate_passport(_sample_request())
    with open(resp.pdf_path, "rb") as f:
        head = f.read(4)
    assert head == b"%PDF"


@pytest.mark.asyncio
async def test_full_payload_includes_all_sections(passport_dir):
    req = _sample_request(
        trajectory=[
            PassportTrajectoryPoint(day=0, mean_high_risk_probability=0.34, lower_ci=0.28, upper_ci=0.42),
            PassportTrajectoryPoint(day=7, mean_high_risk_probability=0.29),
        ],
        reranker_weights=RerankerWeights(),
        ranked_interventions=[
            RerankedCandidate(
                intervention_id=2, intervention_name="CBT", intensity=0.65,
                ppo_policy_score=0.41, simulator_risk_reduction_score=0.68,
                adherence_prior_score=0.7, care_phase_prior_score=0.9,
                patient_preference_score=0.55, raw_risk_reduction=0.18,
                final_score=0.62, rank=1,
                explanation="CBT ranked by care-phase prior and simulator risk reduction.",
                contributing_factors=["care-phase prior", "simulator risk reduction"],
            ),
        ],
        care_path=PassportCarePath(
            phase="practice", review_cadence_days=7,
            recommended_intervention_tones=["CBT", "Exercise"],
            phase_guidance="Skill-building phase.",
        ),
        evidence=[
            PassportEvidenceItem(
                title="CBT meta-analysis", source="PubMed", year=2024,
                url="https://example.org/", summary="22 RCTs, moderate ES.",
            ),
        ],
        narrative_paragraph="You are building momentum.",
        blocked_interventions=[],
        safety_notes=["Re-screen in next check-in."],
    )
    resp = await generate_passport(req)
    for expected in ["risk_snapshot", "trajectory", "care_path",
                     "ranked_interventions", "narrative", "evidence", "safety_notes"]:
        assert expected in resp.sections_included, \
            f"missing {expected} in {resp.sections_included}"
    # No warnings on a fully-populated payload.
    assert resp.warnings == []


@pytest.mark.asyncio
async def test_resolver_round_trip(passport_dir):
    resp = await generate_passport(_sample_request())
    path = resolve_passport_path(resp.passport_id)
    assert path.exists()
    assert path.read_bytes()[:4] == b"%PDF"


def test_resolver_rejects_bad_ids(passport_dir):
    import pytest as _pytest
    with _pytest.raises(FileNotFoundError):
        resolve_passport_path("../etc/passwd")
    with _pytest.raises(FileNotFoundError):
        resolve_passport_path("not-hex-id-$$$")


@pytest.mark.asyncio
async def test_warnings_recorded_for_skipped_sections(passport_dir):
    # Minimum payload — trajectory, care_path, ranked_interventions are all absent.
    resp = await generate_passport(_sample_request())
    joined = " | ".join(resp.warnings)
    assert "trajectory" in joined
    assert "care-path" in joined or "care_path" in joined
    assert "ranked interventions" in joined or "interventions" in joined
