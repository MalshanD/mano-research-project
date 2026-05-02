"""
Researcher Cohort — Privacy & Utility Audit service.

Consumes a previously-generated cohort (``patients.csv``), runs a
k-anonymity check over a caller-chosen set of quasi-identifier columns
plus univariate column summaries, and returns a verdict:

* ``safe``    — k-anonymity passes, no obvious distribution collapse.
* ``review``  — k-anonymity fails OR a column collapsed to one value.
* ``unsafe``  — structural problem (missing columns, empty cohort).

The audit is stateless — we don't persist results. Researchers can
re-run with different ``quasi_identifiers`` / ``k_min`` values cheaply.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

from lib.synthetic.research_cohort_service import (
    load_manifest,
    load_patients_dataframe,
)
from schemas.synthetic.research_audit_schema import (
    CohortAuditRequest,
    CohortAuditResponse,
    ColumnSummary,
    KAnonymityReport,
)

logger = logging.getLogger(__name__)


# ─── Column summaries ────────────────────────────────────────────────────

def _summarise_column(df: pd.DataFrame, col: str) -> ColumnSummary:
    series = df[col]
    dtype = str(series.dtype)
    non_null = int(series.notna().sum())
    unique = int(series.nunique(dropna=True))
    summary = ColumnSummary(
        column=col,
        dtype=dtype,
        non_null_count=non_null,
        unique_count=unique,
        collapsed_to_single_value=(unique <= 1 and non_null > 0),
    )
    if pd.api.types.is_numeric_dtype(series):
        numeric = series.dropna()
        if len(numeric):
            summary.mean = float(numeric.mean())
            summary.stddev = float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0
            summary.min = float(numeric.min())
            summary.max = float(numeric.max())
    else:
        # Top values — cast to str so they always JSON-serialise.
        counts = series.astype(str).value_counts().head(5)
        summary.top_values = {str(k): int(v) for k, v in counts.items()}
    return summary


# ─── k-anonymity ─────────────────────────────────────────────────────────

def _k_anonymity(
    df: pd.DataFrame, quasi_identifiers: List[str], k_min: int,
) -> KAnonymityReport:
    missing = [c for c in quasi_identifiers if c not in df.columns]
    if missing:
        raise ValueError(
            f"Quasi-identifier columns missing from cohort: {missing}",
        )

    # Groupby on the QI set. ``dropna=False`` so missing values still form groups
    # — hiding them would understate the re-id risk.
    groups = df.groupby(quasi_identifiers, dropna=False).size()
    if len(groups) == 0:
        return KAnonymityReport(
            quasi_identifiers=quasi_identifiers,
            k_min_requested=k_min,
            smallest_group_size=0,
            groups_below_k=0,
            **{"pass": False},
        )

    smallest = int(groups.min())
    below = int((groups < k_min).sum())
    example = None
    if below:
        # Pick the smallest group for the reviewer.
        target = groups.idxmin()
        if not isinstance(target, tuple):
            target = (target,)
        example = {
            str(col): str(val) for col, val in zip(quasi_identifiers, target)
        }
    return KAnonymityReport(
        quasi_identifiers=quasi_identifiers,
        k_min_requested=k_min,
        smallest_group_size=smallest,
        groups_below_k=below,
        example_under_anonymised_group=example,
        **{"pass": smallest >= k_min},
    )


# ─── Entry point ─────────────────────────────────────────────────────────

def audit_cohort(request: CohortAuditRequest) -> CohortAuditResponse:
    manifest = load_manifest(request.cohort_id)
    df = load_patients_dataframe(request.cohort_id)

    reasons: List[str] = []
    warnings: List[str] = []

    if len(df) == 0:
        return CohortAuditResponse(
            cohort_id=request.cohort_id,
            num_patients=0,
            overall_verdict="unsafe",
            reasons=["Cohort is empty."],
            k_anonymity=KAnonymityReport(
                quasi_identifiers=request.quasi_identifiers,
                k_min_requested=request.k_min,
                smallest_group_size=0,
                groups_below_k=0,
                **{"pass": False},
            ),
        )

    # k-anonymity — may raise if QI columns are invalid; return 422 upstream.
    k_report = _k_anonymity(df, request.quasi_identifiers, request.k_min)
    if not getattr(k_report, "pass_", False):
        reasons.append(
            f"{k_report.groups_below_k} QI group(s) have fewer than "
            f"{request.k_min} members (smallest: {k_report.smallest_group_size}).",
        )

    # Column summaries — warn on any column that collapsed to a single value.
    summaries = [_summarise_column(df, c) for c in df.columns]
    collapsed = [s.column for s in summaries if s.collapsed_to_single_value]
    if collapsed:
        reasons.append(
            f"{len(collapsed)} column(s) collapsed to a single value: "
            + ", ".join(collapsed),
        )

    # Also compare against manifest's expected ctgan columns — warn if the
    # on-disk file is missing any.
    missing_from_csv = [c for c in manifest.ctgan_columns if c not in df.columns]
    if missing_from_csv:
        warnings.append(
            "Manifest lists columns not present in patients.csv: "
            + ", ".join(missing_from_csv),
        )

    if not reasons:
        verdict = "safe"
    elif any("collapsed" in r for r in reasons):
        # Collapse is structural; a reviewer must decide.
        verdict = "review"
    else:
        verdict = "review"  # k-anonymity failure

    logger.info(
        "research_cohort_audited",
        extra={
            "cohort_id": request.cohort_id,
            "verdict": verdict,
            "k_min": request.k_min,
            "below_k": k_report.groups_below_k,
        },
    )

    return CohortAuditResponse(
        cohort_id=request.cohort_id,
        num_patients=len(df),
        overall_verdict=verdict,
        reasons=reasons,
        k_anonymity=k_report,
        column_summaries=summaries,
        warnings=warnings,
    )
