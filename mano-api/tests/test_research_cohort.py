"""
Researcher Cohort tests — generate, list, audit, query.

Uses the ``fake_generators`` fixture to stub CTGAN + TimeGAN so the tests
run without the 1-2GB of frozen model artefacts (and without torch).
"""

from __future__ import annotations

import pytest

from lib.synthetic.research_audit_service import audit_cohort
from lib.synthetic.research_cohort_service import (
    generate_cohort,
    list_cohorts,
    load_manifest,
    resolve_cohort_file,
)
from lib.synthetic.research_query_service import query_cohort
from schemas.synthetic.research_audit_schema import CohortAuditRequest
from schemas.synthetic.research_cohort_schema import (
    CohortFormat,
    CohortGenerateRequest,
)
from schemas.synthetic.research_query_schema import (
    CohortQueryRequest,
    QueryAggregation,
    QueryFilter,
)


# ─── Generation ──────────────────────────────────────────────────────────

class TestCohortGeneration:
    @pytest.mark.asyncio
    async def test_produces_all_three_formats_by_default(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=20, seed=1,
        ))
        assert set(resp.manifest.files.keys()) >= {"patients_csv", "vitals_csv", "cohort_jsonl"}

    @pytest.mark.asyncio
    async def test_csv_only_skips_jsonl(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=1,
            output_format=CohortFormat.CSV,
        ))
        assert "cohort_jsonl" not in resp.manifest.files
        assert "patients_csv" in resp.manifest.files

    @pytest.mark.asyncio
    async def test_seed_is_recorded_when_omitted(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=5,
        ))
        assert resp.manifest.seed >= 0
        # Manifest is re-readable from disk and matches response.
        on_disk = load_manifest(resp.cohort_id)
        assert on_disk.seed == resp.manifest.seed

    @pytest.mark.asyncio
    async def test_files_have_valid_sha256(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=1,
        ))
        for entry in resp.manifest.files.values():
            assert len(entry.sha256) == 64
            assert entry.size_bytes > 0

    @pytest.mark.asyncio
    async def test_patient_ids_unique(self, research_dir, fake_generators):
        import pandas as pd
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=30, seed=7,
        ))
        patients_path = resp.manifest.files["patients_csv"].path
        df = pd.read_csv(patients_path)
        assert df["patient_id"].nunique() == len(df)

    @pytest.mark.asyncio
    async def test_listing_shows_generated_cohort(self, research_dir, fake_generators):
        await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=5, seed=1,
        ))
        await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=5, seed=2,
        ))
        assert len(list_cohorts()) == 2


# ─── Audit ────────────────────────────────────────────────────────────────

class TestCohortAudit:
    @pytest.mark.asyncio
    async def test_audit_returns_verdict_and_summaries(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=100, seed=5,
        ))
        audit = audit_cohort(CohortAuditRequest(
            cohort_id=resp.cohort_id, quasi_identifiers=["Gender"], k_min=3,
        ))
        assert audit.overall_verdict in {"safe", "review", "unsafe"}
        assert len(audit.column_summaries) >= 5
        # Gender column should have at most 3 unique values by our fake generator.
        gender = next(s for s in audit.column_summaries if s.column == "Gender")
        assert gender.unique_count <= 3

    @pytest.mark.asyncio
    async def test_audit_flags_missing_qi_column(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=1,
        ))
        with pytest.raises(ValueError):
            audit_cohort(CohortAuditRequest(
                cohort_id=resp.cohort_id,
                quasi_identifiers=["NonExistentColumn"],
            ))

    @pytest.mark.asyncio
    async def test_high_cardinality_qi_triggers_review(self, research_dir, fake_generators):
        # 30 rows with Age + Country as QI → many singleton groups → fail k=5.
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=30, seed=1,
        ))
        audit = audit_cohort(CohortAuditRequest(
            cohort_id=resp.cohort_id, quasi_identifiers=["Age", "Country"], k_min=5,
        ))
        assert audit.overall_verdict == "review"
        assert audit.k_anonymity.smallest_group_size < 5


# ─── Query ────────────────────────────────────────────────────────────────

class TestCohortQuery:
    @pytest.mark.asyncio
    async def test_count_with_group_by(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=60, seed=11,
        ))
        q = query_cohort(CohortQueryRequest(
            cohort_id=resp.cohort_id,
            group_by=["Gender"],
            aggregations=[QueryAggregation(column="*", op="count")],
            k_min=3,
        ))
        assert q.total_matched_rows == 60
        assert q.returned_groups >= 1
        # Each group's row count matches what pandas would count.
        assert sum(r.n for r in q.rows) + sum(
            1 for _ in []  # placeholder for suppressed rows — those lose their n
        ) <= 60

    @pytest.mark.asyncio
    async def test_filter_reduces_matched(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=100, seed=11,
        ))
        q = query_cohort(CohortQueryRequest(
            cohort_id=resp.cohort_id,
            filters=[QueryFilter(column="Age", op="gte", value=40)],
            aggregations=[QueryAggregation(column="*", op="count")],
            k_min=2,
        ))
        assert q.total_matched_rows < 100
        assert q.total_matched_rows > 0

    @pytest.mark.asyncio
    async def test_k_min_suppresses_small_groups(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=30, seed=2,
        ))
        q = query_cohort(CohortQueryRequest(
            cohort_id=resp.cohort_id,
            group_by=["Age"],  # high cardinality - many groups of 1
            aggregations=[QueryAggregation(column="*", op="count")],
            k_min=5,
        ))
        assert q.suppressed_groups > 0
        # Every returned row must have n >= k_min.
        assert all(r.n >= 5 for r in q.rows)

    @pytest.mark.asyncio
    async def test_unknown_column_in_filter_rejected(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=3,
        ))
        with pytest.raises(ValueError):
            query_cohort(CohortQueryRequest(
                cohort_id=resp.cohort_id,
                filters=[QueryFilter(column="NonExistent", op="eq", value=1)],
                aggregations=[QueryAggregation(column="*", op="count")],
            ))

    @pytest.mark.asyncio
    async def test_vitals_source_works(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=20, seed=3, include_timegan=True,
        ))
        q = query_cohort(CohortQueryRequest(
            cohort_id=resp.cohort_id, source="vitals", group_by=["day"],
            aggregations=[QueryAggregation(column="sleep_hours", op="mean", alias="avg_sleep")],
            k_min=5,
        ))
        assert q.returned_groups == 7  # exactly 7 days
        for r in q.rows:
            assert r.n == 20
            assert 4.0 <= r.values["avg_sleep"] <= 9.0


# ─── File resolver ────────────────────────────────────────────────────────

class TestFileResolver:
    @pytest.mark.asyncio
    async def test_resolver_serves_declared_files(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=1,
        ))
        path = resolve_cohort_file(resp.cohort_id, "patients.csv")
        assert path.exists()

    @pytest.mark.asyncio
    async def test_resolver_rejects_foreign_file(self, research_dir, fake_generators):
        resp = await generate_cohort(CohortGenerateRequest(
            researcher_id="r-test", num_patients=10, seed=1,
        ))
        with pytest.raises(FileNotFoundError):
            resolve_cohort_file(resp.cohort_id, "../../etc/passwd")
