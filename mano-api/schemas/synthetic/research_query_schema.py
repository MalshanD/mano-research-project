"""
Researcher Cohort — Aggregate Query schemas.

The query endpoint lets researchers slice a cohort without seeing
individual rows. It accepts filters, groupings, and aggregations; the
server enforces a minimum group size (``k_min``) so small groups are
suppressed in the response.

Why not SQL?
-------------
We already persist cohorts as CSV on disk. A dedicated query DSL keeps
the surface area tight and prevents injection-style escapes into the
filesystem / adjacent cohorts. Researchers wanting SQL can download the
CSV and run it locally.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class QueryFilter(BaseModel):
    """Single predicate against a column."""
    column: str
    op: Literal["eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte"] = "eq"
    value: Any = Field(
        ...,
        description="Scalar for eq/ne/gt/gte/lt/lte; list for in / not_in.",
    )


class QueryAggregation(BaseModel):
    column: str
    op: Literal["count", "mean", "stddev", "min", "max", "sum"] = "count"
    alias: Optional[str] = None


class CohortQueryRequest(BaseModel):
    cohort_id: str = Field(..., min_length=8, max_length=64)
    source: Literal["patients", "vitals"] = Field(
        default="patients",
        description="Which file to query: the CTGAN patient table or the "
                    "long-format TimeGAN vitals table.",
    )
    filters: List[QueryFilter] = Field(default_factory=list)
    group_by: List[str] = Field(
        default_factory=list,
        description="Columns to group by. Empty = single aggregate over the "
                    "whole filtered dataset.",
    )
    aggregations: List[QueryAggregation] = Field(
        default_factory=lambda: [QueryAggregation(column="*", op="count")],
        description="At least one aggregation required. ``column='*'`` is "
                    "permitted for count.",
    )
    k_min: int = Field(
        default=5, ge=2, le=100,
        description="Minimum group size; smaller groups are suppressed.",
    )


class CohortQueryRow(BaseModel):
    group: Dict[str, str] = Field(default_factory=dict)
    n: int = Field(..., ge=0, description="Row count in the group pre-suppression.")
    values: Dict[str, float] = Field(default_factory=dict)


class CohortQueryResponse(BaseModel):
    cohort_id: str
    source: Literal["patients", "vitals"]
    total_matched_rows: int
    returned_groups: int
    suppressed_groups: int = Field(
        default=0,
        description="Groups smaller than ``k_min`` that were omitted.",
    )
    rows: List[CohortQueryRow] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
