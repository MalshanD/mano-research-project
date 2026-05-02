"""
Researcher Cohort — Privacy & Utility Audit schemas.

The audit endpoint answers one question: *is this synthetic cohort safe
to share with collaborators outside MANO?* A "pass" is not a privacy
proof, just a practical sanity check — real releases still need a human
reviewer. The audit covers:

* **k-anonymity** over a caller-chosen set of quasi-identifier columns.
  Minimum group size below ``k_min`` flags the cohort as "review".
* **Univariate distributions** — per-column summaries a reviewer can
  eyeball against the training data distribution.
* **Coverage** — whether every column was populated or the generator
  collapsed a category to a single value.

We deliberately do NOT attempt nearest-neighbour distance here. The
frozen CTGAN was trained on a public dataset (Mental Health in Tech
Survey) — distance to that dataset is meaningful only if we also
transport the training rows, which this service must not do.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ColumnSummary(BaseModel):
    column: str
    dtype: str
    non_null_count: int = Field(..., ge=0)
    unique_count: int = Field(..., ge=0)
    # Numeric columns only
    mean: Optional[float] = None
    stddev: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    # Categorical columns only
    top_values: Dict[str, int] = Field(
        default_factory=dict,
        description="Top ~5 values and their counts.",
    )
    collapsed_to_single_value: bool = Field(
        default=False,
        description="True if the whole column has only one distinct value — a "
                    "generator failure mode worth surfacing.",
    )


class KAnonymityReport(BaseModel):
    quasi_identifiers: List[str]
    k_min_requested: int
    smallest_group_size: int
    groups_below_k: int
    pass_: bool = Field(
        ...,
        alias="pass",
        description="True when smallest_group_size >= k_min_requested.",
    )
    example_under_anonymised_group: Optional[Dict[str, str]] = Field(
        default=None,
        description="A single small group, shown for review. Keys are the "
                    "quasi-identifier column values.",
    )

    model_config = {"populate_by_name": True}


class CohortAuditRequest(BaseModel):
    cohort_id: str = Field(..., min_length=8, max_length=64)
    quasi_identifiers: List[str] = Field(
        default_factory=lambda: ["Age", "Gender", "Country"],
        description="Columns treated as quasi-identifiers for k-anonymity. "
                    "Must be a subset of the cohort's ctgan_columns.",
    )
    k_min: int = Field(
        default=5, ge=2, le=100,
        description="Minimum acceptable group size.",
    )


class CohortAuditResponse(BaseModel):
    cohort_id: str
    num_patients: int
    overall_verdict: Literal["safe", "review", "unsafe"]
    reasons: List[str] = Field(default_factory=list)
    k_anonymity: KAnonymityReport
    column_summaries: List[ColumnSummary] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
