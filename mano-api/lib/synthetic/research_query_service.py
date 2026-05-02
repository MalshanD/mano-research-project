"""
Researcher Cohort — Aggregate Query service.

Loads one of a cohort's CSV artefacts (patients or vitals), applies a
list of typed filters, groups, and aggregations, and returns aggregate
rows only. Groups smaller than ``k_min`` are suppressed — this is a
privacy guard, not a query feature: we never leak counts that could
finger-print an individual synthetic record (which could, in turn,
correlate back to a real training row).
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd

from lib.synthetic.research_cohort_service import (
    load_patients_dataframe,
    load_vitals_dataframe,
)
from schemas.synthetic.research_query_schema import (
    CohortQueryRequest,
    CohortQueryResponse,
    CohortQueryRow,
    QueryFilter,
)

logger = logging.getLogger(__name__)


# ─── Filter application ─────────────────────────────────────────────────

def _apply_filter(df: pd.DataFrame, f: QueryFilter) -> pd.DataFrame:
    if f.column not in df.columns:
        raise ValueError(f"Unknown column '{f.column}' in filter.")
    col = df[f.column]
    if f.op == "eq":
        return df[col == f.value]
    if f.op == "ne":
        return df[col != f.value]
    if f.op == "in":
        if not isinstance(f.value, (list, tuple, set)):
            raise ValueError("Filter op 'in' requires a list value.")
        return df[col.isin(list(f.value))]
    if f.op == "not_in":
        if not isinstance(f.value, (list, tuple, set)):
            raise ValueError("Filter op 'not_in' requires a list value.")
        return df[~col.isin(list(f.value))]
    # Numeric comparisons — coerce to numeric so CSV-loaded strings still work.
    try:
        numeric_col = pd.to_numeric(col, errors="coerce")
        numeric_val = float(f.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Filter op '{f.op}' on non-numeric column '{f.column}': {exc}",
        ) from exc
    if f.op == "gt":
        return df[numeric_col > numeric_val]
    if f.op == "gte":
        return df[numeric_col >= numeric_val]
    if f.op == "lt":
        return df[numeric_col < numeric_val]
    if f.op == "lte":
        return df[numeric_col <= numeric_val]
    raise ValueError(f"Unknown filter op '{f.op}'.")


# ─── Aggregation ────────────────────────────────────────────────────────

_AGG_FUNCS = {
    "count": "count",
    "sum": "sum",
    "mean": "mean",
    "stddev": "std",
    "min": "min",
    "max": "max",
}


def _aggregate(
    df: pd.DataFrame, request: CohortQueryRequest,
) -> List[CohortQueryRow]:
    if df.empty:
        return []

    # Validate aggregation columns up front.
    for agg in request.aggregations:
        if agg.column == "*" and agg.op != "count":
            raise ValueError("'*' column is only valid with the 'count' op.")
        if agg.column != "*" and agg.column not in df.columns:
            raise ValueError(f"Unknown column '{agg.column}' in aggregation.")

    # Validate group-by columns.
    for g in request.group_by:
        if g not in df.columns:
            raise ValueError(f"Unknown column '{g}' in group_by.")

    rows: List[CohortQueryRow] = []

    if not request.group_by:
        group_iter = [(tuple(), df)]
    else:
        # ``dropna=False`` so NaN groups surface in the output; researchers often
        # want to see "unknown" as its own bucket.
        group_iter = list(df.groupby(request.group_by, dropna=False))

    for key, group_df in group_iter:
        if not isinstance(key, tuple):
            key = (key,)
        n = int(len(group_df))
        values: dict[str, float] = {}
        for agg in request.aggregations:
            alias = agg.alias or f"{agg.op}_{agg.column}"
            if agg.column == "*" and agg.op == "count":
                values[alias] = float(n)
                continue
            series = group_df[agg.column]
            # For non-count aggs, coerce to numeric. Non-numeric => NaN => skipped.
            if agg.op != "count":
                series = pd.to_numeric(series, errors="coerce").dropna()
            func = _AGG_FUNCS[agg.op]
            if len(series) == 0:
                values[alias] = float("nan")
                continue
            raw = getattr(series, func)()
            # pandas std returns NaN on single-element groups; surface as 0.
            if agg.op == "stddev" and (raw is None or np.isnan(raw)):
                raw = 0.0
            values[alias] = float(raw)
        rows.append(CohortQueryRow(
            group={col: str(val) for col, val in zip(request.group_by, key)},
            n=n,
            values=values,
        ))
    return rows


# ─── Entry point ────────────────────────────────────────────────────────

def query_cohort(request: CohortQueryRequest) -> CohortQueryResponse:
    if not request.aggregations:
        raise ValueError("At least one aggregation is required.")

    if request.source == "patients":
        df = load_patients_dataframe(request.cohort_id)
    else:
        df = load_vitals_dataframe(request.cohort_id)
        if df is None:
            raise FileNotFoundError(
                f"Cohort '{request.cohort_id}' has no vitals file — was "
                "``include_timegan`` set on generation?",
            )

    # Apply filters in declaration order.
    for f in request.filters:
        df = _apply_filter(df, f)

    warnings: List[str] = []
    matched = int(len(df))

    rows = _aggregate(df, request)
    suppressed = 0
    if request.k_min > 1:
        kept: List[CohortQueryRow] = []
        for r in rows:
            if r.n < request.k_min:
                suppressed += 1
                continue
            kept.append(r)
        rows = kept

    if suppressed:
        warnings.append(
            f"{suppressed} group(s) suppressed for being smaller than k_min="
            f"{request.k_min}.",
        )

    logger.info(
        "research_cohort_queried",
        extra={
            "cohort_id": request.cohort_id,
            "source": request.source,
            "matched": matched,
            "returned": len(rows),
            "suppressed": suppressed,
        },
    )

    return CohortQueryResponse(
        cohort_id=request.cohort_id,
        source=request.source,
        total_matched_rows=matched,
        returned_groups=len(rows),
        suppressed_groups=suppressed,
        rows=rows,
        warnings=warnings,
    )
