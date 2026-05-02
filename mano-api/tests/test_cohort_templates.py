"""
Tests for ``lib.synthetic.cohort_templates``.

Each template must:
  * exist in ``list_templates()`` with non-empty descriptors,
  * round-trip through ``build_request`` to a valid
    ``CohortGenerateRequest`` (Pydantic validation passes),
  * carry an ``epsilon`` value within the schema's allowed range,
  * preserve researcher_id and per-call overrides correctly.

Catalog discipline (one named template per common research scenario)
is enforced by an end-to-end test that asserts the keyset.
"""

from __future__ import annotations

import pytest

from lib.synthetic.cohort_templates import build_request, get_template, list_templates
from schemas.synthetic.research_cohort_schema import (
    CohortFormat,
    CohortGenerateRequest,
)


_EXPECTED_NAMES = {
    "anxious_adults_25_35_balanced_gender",
    "stable_elderly_low_risk_baseline",
    "seasonal_depression_winter_cohort",
    "adolescent_high_screen_time_high_anxiety",
    "pre_post_intervention_matched_pair",
}


def test_catalog_has_expected_templates():
    names = {t["name"] for t in list_templates()}
    assert names == _EXPECTED_NAMES


def test_listed_templates_have_non_empty_descriptors():
    for descriptor in list_templates():
        assert descriptor["title"]
        assert descriptor["description"]
        assert descriptor["research_use_case"]
        assert descriptor["privacy_notes"]


def test_get_template_unknown_name_raises_key_error():
    with pytest.raises(KeyError):
        get_template("does_not_exist")


@pytest.mark.parametrize("name", sorted(_EXPECTED_NAMES))
def test_build_request_produces_valid_pydantic_payload(name: str):
    req = build_request(name, researcher_id="test-researcher-001")
    assert isinstance(req, CohortGenerateRequest)
    assert req.researcher_id == "test-researcher-001"
    assert req.num_patients >= 1
    assert req.epsilon is not None
    # All templates default to BOTH for output ergonomics.
    assert req.output_format == CohortFormat.BOTH
    # Each template surfaces its name in the notes for downstream auditors.
    assert req.notes is not None
    assert name in req.notes


def test_build_request_overrides_apply_last():
    req = build_request(
        "anxious_adults_25_35_balanced_gender",
        researcher_id="r-1",
        overrides={"num_patients": 25, "epsilon": 1.0, "include_timegan": False},
    )
    assert req.num_patients == 25
    assert req.epsilon == 1.0
    assert req.include_timegan is False


def test_build_request_overrides_cannot_break_pydantic_validation():
    # epsilon outside the schema range must be rejected by Pydantic.
    with pytest.raises(Exception):
        build_request(
            "anxious_adults_25_35_balanced_gender",
            researcher_id="r-1",
            overrides={"epsilon": 99.0},  # > 20 cap
        )


def test_template_privacy_notes_use_real_privacy_vocabulary():
    """Privacy notes are non-trivial — they should reference at least
    one concept from the real privacy vocabulary (audit / epsilon /
    k-anonymity / re-identification / GDPR / COPPA / IRB)."""
    privacy_terms = ("audit", "epsilon", "k-anonym", "re-identif",
                     "gdpr", "coppa", "irb")
    for t in list_templates():
        notes = t["privacy_notes"].lower()
        assert any(term in notes for term in privacy_terms), (
            f"Template {t['name']!r} privacy notes do not reference "
            f"any privacy vocabulary term: {notes!r}"
        )
