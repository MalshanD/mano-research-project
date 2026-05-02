"""
Researcher Cohort schemas.

What is a "research cohort"?
----------------------------
A researcher-requested batch of synthetic patients, produced by the
frozen CTGAN (tabular demographics + mental-health-survey responses) and,
optionally, the frozen TimeGAN (7-day wearable sequences). Each cohort
is persisted to disk as an immutable artefact with a manifest so results
are reproducible — the seed, model file hashes, and output file hashes
are all recorded.

The research API deliberately produces *de-identified* synthetic data
only — we never expose real patient rows here. That's the whole point
of CTGAN/TimeGAN being in the stack. A separate privacy-audit endpoint
can run k-anonymity / distribution checks before release.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CohortFormat(str, Enum):
    """Export formats the cohort can be rendered in."""
    CSV = "csv"
    JSONL = "jsonl"
    BOTH = "both"


class CohortGenerateRequest(BaseModel):
    researcher_id: str = Field(
        ..., min_length=1, max_length=64,
        description="Who is asking — appears in audit log and manifest.",
    )
    num_patients: int = Field(
        default=50, ge=1, le=1000,
        description="How many synthetic patients to sample. Upper bound of 1000 "
                    "keeps a single generation pass within typical RTX 3050 memory.",
    )
    include_timegan: bool = Field(
        default=True,
        description="Also generate 7-day wearable sequences per patient.",
    )
    seed: Optional[int] = Field(
        default=None, ge=0, le=2**31 - 1,
        description="Random seed. Omit to use a fresh seed recorded in the manifest.",
    )
    output_format: CohortFormat = Field(default=CohortFormat.BOTH)
    notes: Optional[str] = Field(default=None, max_length=500)
    epsilon: Optional[float] = Field(
        default=None, ge=0.01, le=20.0,
        description="Differential-privacy epsilon claimed for this generation. "
                    "Recorded on the audit report — the audit does not verify "
                    "epsilon (that is a separate analysis) but ships it on the "
                    "audit record so privacy claims and audit results travel "
                    "together.",
    )
    skip_audit: bool = Field(
        default=False,
        description="When True the audit is bypassed entirely. Reserved for "
                    "test runs and benchmarking — production cohorts MUST "
                    "carry an audit.",
    )


class CohortFileEntry(BaseModel):
    path: str
    size_bytes: int = Field(..., ge=0)
    sha256: str
    row_count: int = Field(..., ge=0)


class CohortManifest(BaseModel):
    cohort_id: str
    researcher_id: str
    num_patients: int
    include_timegan: bool
    seed: int
    created_at: datetime
    ctgan_columns: List[str]
    timegan_signals: List[str] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Hashes / versions of the frozen model artefacts used.",
    )
    files: Dict[str, CohortFileEntry] = Field(
        default_factory=dict,
        description="Keyed by logical file name "
                    "(patients_csv, vitals_csv, cohort_jsonl).",
    )
    notes: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    audit_attached: bool = Field(
        default=False,
        description="True iff a SynthAuditReport accompanies this manifest "
                    "in the cohort directory (filename: audit.json).",
    )
    audit_overall_severity: Optional[str] = Field(
        default=None,
        description="Roll-up severity of the attached audit (ok | warn | fail). "
                    "Surfaced here so listing endpoints don't have to load the "
                    "full audit JSON to render the cohort's safety badge.",
    )


class CohortGenerateResponse(BaseModel):
    cohort_id: str
    manifest: CohortManifest
    download_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="Public URLs the frontend can use to pull each output file.",
    )


class CohortListResponse(BaseModel):
    count: int
    cohorts: List[CohortManifest] = Field(default_factory=list)
