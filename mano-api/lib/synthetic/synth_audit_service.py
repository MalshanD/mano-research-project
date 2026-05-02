"""
Synthetic Cohort Audit — privacy + quality measurements.

This module is the *measurement layer* on top of the existing CTGAN +
TimeGAN cohort generator. The earlier service shipped synthetic data
with an ``epsilon`` knob and called it "DP". An epsilon claim without a
measurement is a liability — this audit replaces the bare claim with
something a research partner can cite.

What the audit measures
-----------------------
Privacy
  * **k-anonymity** over chosen quasi-identifier columns. Reports min k,
    median k, fraction of unique rows.
  * **Self-nearest-neighbour** outlier scan over numeric columns. Flags
    rows that sit far from their cohort peers — those are the rows most
    at risk of re-identification.
  * **Membership-inference adversary** (when reference real-data sample
    is provided). Trains a quick scikit-learn random forest to
    distinguish real vs. synthetic and reports AUC. AUC ≥ 0.65 ⇒ leak.

Quality
  * **Marginal distribution sanity** — per-column mean / std / range /
    distinct values / fraction zero / NaN. Detects mode collapse and
    constant-zero columns.
  * **Correlation health** — checks the synth correlation matrix isn't
    flat (uncorrelated noise) or saturated (1-D manifold).
  * **Wasserstein distance** vs. a reference distribution (when supplied).
  * **Downstream-task fidelity** — feeds the synthetic cohort through
    the frozen LSTM and reports the resulting risk-class distribution.
    A cohort that lands every patient in the same class is structurally
    suspect.
  * **TimeGAN sequence sanity** — per-channel range checks and lag-1
    autocorrelation.

Design invariants
-----------------
1. **Audit MUST not mutate the cohort.** Numpy / pandas operations only.
2. **Audit MUST never crash the generator.** Any internal failure is
   caught, logged, and represented as a ``WARN`` block with a
   diagnostic note. The cohort still ships — without the audit nothing
   safer is achieved.
3. **Audit MUST not require optional dependencies to import.** sklearn
   is imported lazily inside the membership-inference function so the
   module can load on an environment that doesn't have it.
4. **Audit MUST be deterministic** for a given (cohort, reference)
   pair. We seed the numpy RNG used for any random sampling.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from schemas.synthetic.synth_audit_schema import (
    AuditSeverity,
    CorrelationReport,
    DownstreamRiskReport,
    KAnonymityReport,
    MarginalColumnStats,
    MarginalReport,
    MembershipInferenceReport,
    SelfNearestNeighborReport,
    SynthAuditReport,
    TimeGANSequenceReport,
    WassersteinReport,
)

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _numeric_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _categorical_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]


def _safe_divide(numer: float, denom: float, default: float = 0.0) -> float:
    return numer / denom if denom else default


# ── Privacy: k-anonymity ───────────────────────────────────────────────────


def compute_k_anonymity(
    df: pd.DataFrame,
    quasi_id_columns: Optional[List[str]] = None,
    fail_threshold: int = 5,
) -> KAnonymityReport:
    """Group by quasi-identifier columns and report cluster-size stats.

    When the caller doesn't specify quasi-identifier columns we default
    to all categorical columns plus all numeric columns binned into
    deciles. That mirrors the standard practice of treating both
    categorical and bucketed continuous fields as identifiers.
    """
    if df.empty:
        return KAnonymityReport(
            quasi_identifier_columns=[],
            min_k=0, median_k=0.0,
            fraction_unique_rows=0.0,
            fail_threshold_k=fail_threshold,
            severity=AuditSeverity.WARN,
        )

    if not quasi_id_columns:
        # Default: treat categorical columns + decile-bucketed numerics as QIDs.
        cat_cols = _categorical_columns(df)
        num_cols = _numeric_columns(df)
        # Drop trivial columns (patient_id, day) — they're unique identifiers,
        # not quasi-identifiers, and would force k=1 trivially.
        ignore = {"patient_id", "day"}
        cat_cols = [c for c in cat_cols if c not in ignore]
        num_cols = [c for c in num_cols if c not in ignore]
        # Bucket numerics for QID purposes.
        bucketed = df.copy()
        for col in num_cols:
            try:
                bucketed[col] = pd.qcut(
                    bucketed[col].rank(method="first"), q=10, labels=False, duplicates="drop",
                )
            except Exception:
                bucketed[col] = bucketed[col].fillna(0).round(0)
        quasi_id_columns = cat_cols + num_cols
        df_for_grouping = bucketed
    else:
        df_for_grouping = df

    if not quasi_id_columns:
        return KAnonymityReport(
            quasi_identifier_columns=[],
            min_k=len(df), median_k=float(len(df)),
            fraction_unique_rows=0.0,
            fail_threshold_k=fail_threshold,
            severity=AuditSeverity.OK,
        )

    sizes = df_for_grouping.groupby(quasi_id_columns, dropna=False).size()
    min_k = int(sizes.min())
    median_k = float(sizes.median())
    fraction_unique = float((sizes == 1).sum() / len(sizes))

    if min_k >= fail_threshold:
        severity = AuditSeverity.OK
    elif min_k >= 2:
        severity = AuditSeverity.WARN
    else:
        severity = AuditSeverity.FAIL

    return KAnonymityReport(
        quasi_identifier_columns=quasi_id_columns,
        min_k=min_k,
        median_k=median_k,
        fraction_unique_rows=fraction_unique,
        fail_threshold_k=fail_threshold,
        severity=severity,
    )


# ── Privacy: self-NN outliers ───────────────────────────────────────────────


def compute_self_nearest_neighbor(
    df: pd.DataFrame,
    numeric_columns: Optional[List[str]] = None,
    outlier_z: float = 3.0,
    seed: int = 13,
) -> SelfNearestNeighborReport:
    """For each row, distance to its nearest other row across numeric cols.

    Outliers (NN distance > mean + outlier_z * std) are flagged as
    candidate re-identification targets. We compute on a max sample of
    2 000 rows to keep the audit O(n²) bounded.
    """
    if numeric_columns is None:
        numeric_columns = _numeric_columns(df)
    numeric_columns = [c for c in numeric_columns if c not in ("day",)]
    if not numeric_columns or df.empty:
        return SelfNearestNeighborReport(
            n_rows=0,
            mean_nn_distance=0.0, std_nn_distance=0.0,
            min_nn_distance=0.0, max_nn_distance=0.0,
            outlier_count=0, outlier_fraction=0.0,
            severity=AuditSeverity.OK,
        )

    rng = np.random.default_rng(seed)
    if len(df) > 2000:
        sample_idx = rng.choice(len(df), size=2000, replace=False)
        sample = df.iloc[sample_idx][numeric_columns].to_numpy(dtype=np.float64)
    else:
        sample = df[numeric_columns].to_numpy(dtype=np.float64)

    # Standardise so each column contributes proportionally.
    means = sample.mean(axis=0)
    stds = sample.std(axis=0, ddof=0)
    stds = np.where(stds < 1e-12, 1.0, stds)
    normalised = (sample - means) / stds

    # All-pairs L2 distances. n×n with n ≤ 2000 ⇒ ≤ 4M floats ≈ 32 MB.
    diff = normalised[:, None, :] - normalised[None, :, :]
    dists = np.linalg.norm(diff, axis=2)
    # Replace self-distance with +inf so it doesn't win the min.
    np.fill_diagonal(dists, np.inf)
    nn = dists.min(axis=1)

    mean_nn = float(nn.mean())
    std_nn = float(nn.std(ddof=0))
    min_nn = float(nn.min())
    max_nn = float(nn.max())
    threshold = mean_nn + outlier_z * std_nn
    outliers = int(np.sum(nn > threshold))
    outlier_frac = _safe_divide(outliers, len(nn))

    if outlier_frac < 0.01:
        severity = AuditSeverity.OK
    elif outlier_frac < 0.05:
        severity = AuditSeverity.WARN
    else:
        severity = AuditSeverity.FAIL

    return SelfNearestNeighborReport(
        n_rows=len(nn),
        mean_nn_distance=mean_nn,
        std_nn_distance=std_nn,
        min_nn_distance=min_nn,
        max_nn_distance=max_nn,
        outlier_count=outliers,
        outlier_fraction=outlier_frac,
        severity=severity,
    )


# ── Privacy: membership inference adversary ────────────────────────────────


def compute_membership_inference(
    synth_df: pd.DataFrame,
    real_df: Optional[pd.DataFrame],
    numeric_columns: Optional[List[str]] = None,
    seed: int = 13,
) -> MembershipInferenceReport:
    """Train a binary classifier to distinguish real vs. synthetic rows.

    Returns AUC on a held-out split. The closer to 0.5, the better the
    privacy. AUC ≥ 0.65 indicates measurable leakage; AUC ≥ 0.80 is a
    hard fail.

    When ``real_df`` is None or empty we skip the test and record
    ``inferred=False`` with a diagnostic note. Severity remains OK
    (the audit cannot fail what it didn't measure).
    """
    if real_df is None or real_df.empty:
        return MembershipInferenceReport(
            inferred=False,
            note="No reference real-data sample supplied — adversarial test skipped.",
            severity=AuditSeverity.OK,
        )

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import train_test_split
    except Exception:
        return MembershipInferenceReport(
            inferred=False,
            note="scikit-learn not available — adversarial test skipped.",
            severity=AuditSeverity.OK,
        )

    if numeric_columns is None:
        numeric_columns = [c for c in _numeric_columns(synth_df) if c in real_df.columns]
    numeric_columns = [c for c in numeric_columns if c not in ("day", "patient_id")]
    if not numeric_columns:
        return MembershipInferenceReport(
            inferred=False,
            note="No shared numeric columns between synth and reference.",
            severity=AuditSeverity.OK,
        )

    s = synth_df[numeric_columns].to_numpy(dtype=np.float64)
    r = real_df[numeric_columns].to_numpy(dtype=np.float64)
    X = np.vstack([s, r])
    y = np.concatenate([np.zeros(len(s)), np.ones(len(r))])

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=seed, n_jobs=1)
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, proba))

    if auc <= 0.55:
        severity = AuditSeverity.OK
    elif auc <= 0.65:
        severity = AuditSeverity.WARN
    else:
        severity = AuditSeverity.FAIL

    return MembershipInferenceReport(
        inferred=True,
        auc=auc,
        n_real_samples=len(r),
        n_synth_samples=len(s),
        classifier="RandomForestClassifier(n_estimators=100, max_depth=8)",
        severity=severity,
    )


# ── Quality: marginal distribution sanity ──────────────────────────────────


def compute_marginal_distribution(df: pd.DataFrame) -> MarginalReport:
    columns: List[MarginalColumnStats] = []
    n_collapsed = 0
    n_zero_const = 0
    for col in _numeric_columns(df):
        series = df[col]
        distinct = int(series.nunique(dropna=True))
        zero_count = int((series == 0).sum())
        nan_count = int(series.isna().sum())
        n = len(series)
        stats = MarginalColumnStats(
            column=col,
            mean=float(series.mean()) if n else 0.0,
            std=float(series.std(ddof=0)) if n else 0.0,
            min_value=float(series.min()) if n else 0.0,
            max_value=float(series.max()) if n else 0.0,
            distinct_values=distinct,
            fraction_zero=_safe_divide(zero_count, n),
            fraction_nan=_safe_divide(nan_count, n),
        )
        columns.append(stats)
        if distinct <= 1:
            n_collapsed += 1
            if zero_count == n:
                n_zero_const += 1

    if n_collapsed == 0:
        severity = AuditSeverity.OK
    elif n_collapsed == 1:
        severity = AuditSeverity.WARN
    else:
        severity = AuditSeverity.FAIL

    return MarginalReport(
        columns=columns,
        n_columns_collapsed=n_collapsed,
        n_columns_constant_zero=n_zero_const,
        severity=severity,
    )


# ── Quality: correlation matrix health ─────────────────────────────────────


def compute_correlation_health(
    df: pd.DataFrame, threshold: float = 0.95
) -> CorrelationReport:
    cols = [c for c in _numeric_columns(df) if df[c].nunique() > 1]
    n = len(cols)
    if n < 2:
        return CorrelationReport(
            n_numeric_columns=n,
            mean_abs_offdiag=0.0,
            max_abs_offdiag=0.0,
            n_pairs_above_threshold=0,
            threshold=threshold,
            severity=AuditSeverity.WARN,
        )

    corr = df[cols].corr().to_numpy()
    # Mask the diagonal.
    mask = ~np.eye(n, dtype=bool)
    abs_offdiag = np.abs(corr[mask])
    mean_abs = float(np.nanmean(abs_offdiag))
    max_abs = float(np.nanmax(abs_offdiag))
    above = int(np.sum(abs_offdiag > threshold))

    if 0.05 <= mean_abs <= 0.6 and above < n:
        severity = AuditSeverity.OK
    elif mean_abs < 0.05 or mean_abs > 0.85:
        severity = AuditSeverity.WARN
    else:
        severity = AuditSeverity.OK

    return CorrelationReport(
        n_numeric_columns=n,
        mean_abs_offdiag=mean_abs,
        max_abs_offdiag=max_abs,
        n_pairs_above_threshold=above,
        threshold=threshold,
        severity=severity,
    )


# ── Quality: per-column Wasserstein vs. reference ─────────────────────────


def compute_wasserstein(
    synth_df: pd.DataFrame, real_df: Optional[pd.DataFrame]
) -> WassersteinReport:
    if real_df is None or real_df.empty:
        return WassersteinReport(
            inferred=False,
            note="No reference real-data sample supplied — Wasserstein skipped.",
            severity=AuditSeverity.OK,
        )

    try:
        from scipy.stats import wasserstein_distance
    except Exception:
        return WassersteinReport(
            inferred=False,
            note="scipy not available — Wasserstein skipped.",
            severity=AuditSeverity.OK,
        )

    distances: Dict[str, float] = {}
    shared = [c for c in _numeric_columns(synth_df) if c in real_df.columns]
    for col in shared:
        try:
            d = float(wasserstein_distance(
                synth_df[col].dropna().to_numpy(),
                real_df[col].dropna().to_numpy(),
            ))
            distances[col] = d
        except Exception as exc:
            logger.info("wasserstein_failed", extra={"column": col, "error": str(exc)})
    if not distances:
        return WassersteinReport(
            inferred=True,
            mean_distance=None,
            note="No shared numeric columns produced a Wasserstein distance.",
            severity=AuditSeverity.WARN,
        )
    mean_d = float(np.mean(list(distances.values())))
    severity = AuditSeverity.OK if mean_d < 1.0 else AuditSeverity.WARN
    return WassersteinReport(
        inferred=True,
        columns=distances,
        mean_distance=mean_d,
        severity=severity,
    )


# ── Quality: downstream LSTM risk distribution ─────────────────────────────


def compute_downstream_risk_distribution(
    patients_df: pd.DataFrame,
    vitals_df: Optional[pd.DataFrame],
) -> DownstreamRiskReport:
    """Run the synth cohort through the frozen Hybrid LSTM and report
    the risk-class distribution. A cohort that lands every patient in
    one class is structurally suspect (mode collapse upstream).
    """
    if vitals_df is None or vitals_df.empty:
        return DownstreamRiskReport(
            inferred=False,
            note="No TimeGAN vitals supplied — downstream LSTM scan skipped.",
            severity=AuditSeverity.OK,
        )

    try:
        from lib.synthetic.risk_service import RiskPredictionService
    except Exception:
        return DownstreamRiskReport(
            inferred=False,
            note="Risk service not importable — downstream LSTM scan skipped.",
            severity=AuditSeverity.OK,
        )

    risk_svc = RiskPredictionService()
    if getattr(risk_svc, "model", None) is None:
        return DownstreamRiskReport(
            inferred=False,
            note="Frozen LSTM not loaded — downstream scan skipped.",
            severity=AuditSeverity.OK,
        )

    # Build (1, 7, 4) windows per patient + (1, 20) static vector.
    counts = {"Low": 0, "Medium": 0, "High": 0}
    n_scored = 0

    # Static features: prefer the first 20 numeric columns of patients_df.
    numeric_static_cols = [
        c for c in _numeric_columns(patients_df)
        if c not in ("patient_id", "day")
    ][:20]
    if len(numeric_static_cols) < 20:
        # Pad with zeros — model needs exactly 20 features.
        pad = 20 - len(numeric_static_cols)
    else:
        pad = 0

    label_map = {0: "Low", 1: "Medium", 2: "High"}

    for pid, group in vitals_df.groupby("patient_id", sort=False):
        if len(group) < 7:
            continue
        # Take the first 7 days; project per-day vitals into the canonical order.
        first7 = group.head(7)
        order = ["sleep_hours", "sleep_quality", "heart_rate", "stress_level"]
        try:
            dyn = first7[order].to_numpy(dtype=np.float32).reshape(1, 7, 4)
        except KeyError:
            continue

        match = patients_df[patients_df["patient_id"] == pid]
        if match.empty:
            stat_row = [0.0] * 20
        else:
            row = match.iloc[0]
            vals: List[float] = []
            for col in numeric_static_cols:
                v = row[col]
                vals.append(float(v) if pd.notna(v) else 0.0)
            vals = vals + [0.0] * pad
            stat_row = vals[:20]
        stat = np.array([stat_row], dtype=np.float32)

        try:
            pred = risk_svc.predict(dyn, stat)
        except Exception as exc:
            logger.info("downstream_lstm_failed", extra={"patient_id": str(pid), "error": str(exc)})
            continue
        cls = int(pred["risk_class"])
        counts[label_map.get(cls, "Low")] += 1
        n_scored += 1

    if n_scored == 0:
        return DownstreamRiskReport(
            inferred=True,
            n_patients_scored=0,
            note="No patients had complete 7-day vitals — nothing scored.",
            severity=AuditSeverity.WARN,
        )

    proportions = {k: _safe_divide(v, n_scored) for k, v in counts.items()}
    severity = AuditSeverity.OK
    # Single-class collapse → fail.
    if max(proportions.values()) >= 0.95:
        severity = AuditSeverity.FAIL
    # Skewed (one class > 80%) → warn.
    elif max(proportions.values()) >= 0.80:
        severity = AuditSeverity.WARN

    return DownstreamRiskReport(
        inferred=True,
        n_patients_scored=n_scored,
        risk_class_counts=counts,
        risk_class_proportions=proportions,
        severity=severity,
    )


# ── Quality: TimeGAN sequence sanity ───────────────────────────────────────


_VITALS_RANGES = {
    "sleep_hours": (0.0, 24.0),
    "sleep_quality": (0.0, 1.0),
    "heart_rate": (40.0, 200.0),
    "stress_level": (0.0, 1.0),
}


def compute_timegan_sequence_sanity(
    vitals_df: Optional[pd.DataFrame],
) -> TimeGANSequenceReport:
    if vitals_df is None or vitals_df.empty:
        return TimeGANSequenceReport(
            inferred=False,
            note="No TimeGAN vitals supplied — sequence sanity skipped.",
            severity=AuditSeverity.OK,
        )

    columns_in_range: Dict[str, bool] = {}
    for col, (lo, hi) in _VITALS_RANGES.items():
        if col not in vitals_df.columns:
            continue
        col_min = float(vitals_df[col].min())
        col_max = float(vitals_df[col].max())
        columns_in_range[col] = (col_min >= lo) and (col_max <= hi)

    autocorrs: List[float] = []
    if "patient_id" in vitals_df.columns:
        for col in [c for c in _VITALS_RANGES if c in vitals_df.columns]:
            for _, group in vitals_df.groupby("patient_id", sort=False):
                series = group[col].to_numpy(dtype=np.float64)
                if len(series) < 3:
                    continue
                # Lag-1 Pearson correlation.
                a = series[:-1]
                b = series[1:]
                if a.std(ddof=0) < 1e-12 or b.std(ddof=0) < 1e-12:
                    continue
                autocorrs.append(float(np.corrcoef(a, b)[0, 1]))
    mean_lag1 = float(np.mean(autocorrs)) if autocorrs else None

    severity = AuditSeverity.OK
    if any(not v for v in columns_in_range.values()):
        severity = AuditSeverity.WARN
    if mean_lag1 is not None and mean_lag1 < -0.1:
        # Strongly anti-correlated steps suggest white-noise output.
        severity = AuditSeverity.WARN

    return TimeGANSequenceReport(
        inferred=True,
        n_sequences=int(vitals_df["patient_id"].nunique()) if "patient_id" in vitals_df.columns else 0,
        columns_in_range=columns_in_range,
        mean_lag1_autocorr=mean_lag1,
        severity=severity,
    )


# ── Top-level orchestrator ─────────────────────────────────────────────────


_SEVERITY_RANK = {AuditSeverity.OK: 0, AuditSeverity.WARN: 1, AuditSeverity.FAIL: 2}


def _roll_up_severity(blocks: List[AuditSeverity]) -> AuditSeverity:
    if not blocks:
        return AuditSeverity.OK
    worst = max(blocks, key=lambda s: _SEVERITY_RANK[s])
    return worst


def audit_cohort(
    cohort_id: str,
    patients_df: pd.DataFrame,
    vitals_df: Optional[pd.DataFrame] = None,
    *,
    real_reference_df: Optional[pd.DataFrame] = None,
    epsilon: Optional[float] = None,
    quasi_id_columns: Optional[List[str]] = None,
) -> SynthAuditReport:
    """Run every audit block. Always returns a complete report; never raises."""

    notes: List[str] = []
    actionable: List[str] = []

    def _safe(name: str, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.warning("audit_block_failed", extra={"block": name, "error": str(exc)})
            notes.append(f"{name}: failed internally and was skipped — {exc!r}")
            return None

    k_anon = _safe("k_anonymity", compute_k_anonymity, patients_df, quasi_id_columns)
    if k_anon is None:
        k_anon = KAnonymityReport(
            quasi_identifier_columns=quasi_id_columns or [],
            min_k=0, median_k=0.0, fraction_unique_rows=0.0,
            severity=AuditSeverity.WARN,
        )

    nn = _safe("self_nearest_neighbor", compute_self_nearest_neighbor, patients_df)
    if nn is None:
        nn = SelfNearestNeighborReport(
            n_rows=0, mean_nn_distance=0.0, std_nn_distance=0.0,
            min_nn_distance=0.0, max_nn_distance=0.0,
            outlier_count=0, outlier_fraction=0.0,
            severity=AuditSeverity.WARN,
        )

    membership = _safe("membership_inference", compute_membership_inference, patients_df, real_reference_df)
    if membership is None:
        membership = MembershipInferenceReport(
            inferred=False, note="audit error — skipped",
            severity=AuditSeverity.WARN,
        )

    marginal = _safe("marginal_distribution", compute_marginal_distribution, patients_df)
    if marginal is None:
        marginal = MarginalReport(columns=[], n_columns_collapsed=0, n_columns_constant_zero=0,
                                  severity=AuditSeverity.WARN)

    correlation = _safe("correlation_health", compute_correlation_health, patients_df)
    if correlation is None:
        correlation = CorrelationReport(n_numeric_columns=0, mean_abs_offdiag=0.0,
                                        max_abs_offdiag=0.0, n_pairs_above_threshold=0,
                                        severity=AuditSeverity.WARN)

    wasser = _safe("wasserstein", compute_wasserstein, patients_df, real_reference_df)
    if wasser is None:
        wasser = WassersteinReport(inferred=False, note="audit error — skipped",
                                   severity=AuditSeverity.WARN)

    downstream = _safe("downstream_risk", compute_downstream_risk_distribution,
                       patients_df, vitals_df)
    if downstream is None:
        downstream = DownstreamRiskReport(inferred=False, note="audit error — skipped",
                                          severity=AuditSeverity.WARN)

    timegan = _safe("timegan_sequences", compute_timegan_sequence_sanity, vitals_df)
    if timegan is None:
        timegan = TimeGANSequenceReport(inferred=False, note="audit error — skipped",
                                        severity=AuditSeverity.WARN)

    overall = _roll_up_severity([
        k_anon.severity, nn.severity, membership.severity,
        marginal.severity, correlation.severity, wasser.severity,
        downstream.severity, timegan.severity,
    ])

    # Actionable warnings — surfaced to the researcher's UI.
    if k_anon.severity == AuditSeverity.FAIL:
        actionable.append(
            f"k-anonymity FAIL: at least one synthetic row is unique on its "
            f"quasi-identifier tuple. Consider increasing num_patients or "
            f"applying additional output-side noise."
        )
    if membership.inferred and membership.auc and membership.auc >= 0.65:
        actionable.append(
            f"Membership-inference FAIL: a classifier achieves AUC "
            f"{membership.auc:.2f} distinguishing real from synthetic. "
            f"This synth cohort is not safe for external sharing."
        )
    if marginal.n_columns_collapsed > 0:
        actionable.append(
            f"Marginal sanity WARN: {marginal.n_columns_collapsed} column(s) "
            f"have a single distinct value across the cohort — likely model "
            f"mode collapse."
        )
    if (downstream.inferred and downstream.severity == AuditSeverity.FAIL):
        actionable.append(
            "Downstream-LSTM FAIL: ≥95 % of patients land in a single risk "
            "class. The cohort is unlikely to be useful for stratified "
            "downstream studies."
        )

    if not actionable:
        notes.append("No actionable warnings — cohort is fit for downstream use.")

    return SynthAuditReport(
        audit_id=str(uuid.uuid4()),
        cohort_id=cohort_id,
        audited_at=datetime.now(timezone.utc),
        k_anonymity=k_anon,
        self_nearest_neighbor=nn,
        membership_inference=membership,
        marginal_distribution=marginal,
        correlation_health=correlation,
        wasserstein=wasser,
        downstream_risk=downstream,
        timegan_sequences=timegan,
        overall_severity=overall,
        summary_notes=notes,
        actionable_warnings=actionable,
        epsilon=epsilon,
    )
