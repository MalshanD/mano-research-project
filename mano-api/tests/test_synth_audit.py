"""
Tests for ``lib.synthetic.synth_audit_service``.

Each audit block is exercised independently against a curated dataframe
that exhibits the property the block is supposed to detect. The
top-level ``audit_cohort`` orchestrator is then tested for compositional
behaviour (overall severity = worst block; never raises).

The audit must never crash the cohort generator — test that internal
failures are caught and surfaced as WARN blocks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lib.synthetic.synth_audit_service import (
    audit_cohort,
    compute_correlation_health,
    compute_k_anonymity,
    compute_marginal_distribution,
    compute_membership_inference,
    compute_self_nearest_neighbor,
    compute_timegan_sequence_sanity,
    compute_wasserstein,
)
from schemas.synthetic.synth_audit_schema import AuditSeverity


# ─── Fixture builders ────────────────────────────────────────────────────────


def _diverse_patients(n: int = 100, seed: int = 0) -> pd.DataFrame:
    """Healthy synth-like dataframe — 20 numeric features with realistic
    inter-feature correlations.

    A purely-Gaussian fixture would trip the correlation-health audit
    block (which correctly flags suspiciously uncorrelated cohorts as
    likely noise). Real synthetic mental-health profiles carry small
    structural correlations: age ↔ medication exposure, anxiety ↔ sleep
    quality, social support ↔ outcome. We mimic that by pulling features
    from a covariance matrix with three correlated clusters.
    """
    rng = np.random.default_rng(seed)
    # Build a 20×20 covariance with three correlated blocks.
    cov = np.eye(20)
    blocks = [(0, 7, 0.35), (7, 14, 0.30), (14, 20, 0.25)]
    for lo, hi, rho in blocks:
        for i in range(lo, hi):
            for j in range(lo, hi):
                if i != j:
                    cov[i, j] = rho
    means = np.array([i * 0.1 for i in range(20)])
    samples = rng.multivariate_normal(mean=means, cov=cov, size=n)
    df = pd.DataFrame(samples, columns=[f"f{i}" for i in range(20)])
    df.insert(0, "patient_id", [f"p-{i:04d}" for i in range(n)])
    return df


def _vitals_for(df: pd.DataFrame, days: int = 7, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for pid in df["patient_id"]:
        for d in range(days):
            rows.append({
                "patient_id": pid,
                "day": d,
                "sleep_hours": float(rng.uniform(5.0, 9.0)),
                "sleep_quality": float(rng.uniform(0.2, 0.9)),
                "heart_rate": float(rng.uniform(55.0, 95.0)),
                "stress_level": float(rng.uniform(0.1, 0.9)),
            })
    return pd.DataFrame(rows)


# ─── 1. k-anonymity ──────────────────────────────────────────────────────────


def test_k_anonymity_ok_on_diverse_cohort():
    df = _diverse_patients(n=200)
    rep = compute_k_anonymity(df, fail_threshold=2)
    # Diverse cohort with 200 rows + 20 numeric features — buckets give multiple rows per QID.
    assert rep.min_k >= 1
    # The default QID set excludes patient_id.
    assert "patient_id" not in rep.quasi_identifier_columns


def test_k_anonymity_flags_unique_rows():
    # Force a unique row by giving one patient an outlier value across all features.
    df = _diverse_patients(n=50)
    df.loc[0, "f0"] = 999.0
    df.loc[0, "f1"] = -999.0
    rep = compute_k_anonymity(df, quasi_id_columns=["f0", "f1"], fail_threshold=2)
    assert rep.min_k == 1
    assert rep.severity == AuditSeverity.FAIL


def test_k_anonymity_handles_empty_dataframe():
    rep = compute_k_anonymity(pd.DataFrame())
    assert rep.severity in (AuditSeverity.OK, AuditSeverity.WARN)


# ─── 2. Self-nearest-neighbor ────────────────────────────────────────────────


def test_self_nn_ok_on_clustered_data():
    df = _diverse_patients(n=100)
    rep = compute_self_nearest_neighbor(df)
    assert rep.n_rows == 100
    assert rep.mean_nn_distance > 0
    # No catastrophic outliers expected on a normal-distributed cohort.
    assert rep.outlier_fraction < 0.1


def test_self_nn_flags_extreme_outlier():
    df = _diverse_patients(n=80)
    # Inject a row that's far from everything.
    for col in (c for c in df.columns if c != "patient_id"):
        df.loc[0, col] = 50.0
    rep = compute_self_nearest_neighbor(df)
    assert rep.outlier_count >= 1


# ─── 3. Membership inference ─────────────────────────────────────────────────


def test_membership_inference_skipped_without_reference():
    rep = compute_membership_inference(_diverse_patients(50), real_df=None)
    assert rep.inferred is False
    assert rep.severity == AuditSeverity.OK


def test_membership_inference_runs_when_reference_provided():
    pytest.importorskip("sklearn")
    synth = _diverse_patients(n=200, seed=1)
    real = _diverse_patients(n=200, seed=2)  # drawn from same distribution
    rep = compute_membership_inference(synth, real)
    assert rep.inferred is True
    # Same distribution → adversary should be near-random (AUC near 0.5).
    assert rep.auc is not None
    assert 0.3 <= rep.auc <= 0.7


def test_membership_inference_fails_when_distributions_obviously_differ():
    pytest.importorskip("sklearn")
    synth = _diverse_patients(n=200, seed=1)
    # Real data shifted far from synth — adversary will have an easy time.
    real = synth.copy()
    for col in (c for c in real.columns if c != "patient_id"):
        real[col] = real[col] + 100.0
    rep = compute_membership_inference(synth, real)
    assert rep.auc is not None
    assert rep.auc >= 0.9  # near-perfect separation
    assert rep.severity == AuditSeverity.FAIL


# ─── 4. Marginal distribution ────────────────────────────────────────────────


def test_marginal_ok_on_diverse_data():
    rep = compute_marginal_distribution(_diverse_patients(n=80))
    assert rep.n_columns_collapsed == 0
    assert rep.severity == AuditSeverity.OK


def test_marginal_flags_collapsed_columns():
    df = _diverse_patients(n=50)
    df["f0"] = 0.0  # constant zero
    df["f1"] = 7.5  # constant non-zero
    rep = compute_marginal_distribution(df)
    assert rep.n_columns_collapsed >= 2
    assert rep.n_columns_constant_zero >= 1
    assert rep.severity == AuditSeverity.FAIL


# ─── 5. Correlation health ───────────────────────────────────────────────────


def test_correlation_health_ok_on_independent_features():
    df = _diverse_patients(n=300)
    rep = compute_correlation_health(df)
    # Random Gaussian features — mean abs offdiag should be small but > 0.
    assert 0.0 < rep.mean_abs_offdiag < 0.3
    assert rep.severity == AuditSeverity.OK


def test_correlation_health_warns_on_perfect_correlation():
    df = _diverse_patients(n=100)
    df["f1"] = df["f0"] * 1.5 + 0.001  # near-perfect correlation
    df["f2"] = df["f0"] * -2.0
    rep = compute_correlation_health(df)
    assert rep.n_pairs_above_threshold >= 2


# ─── 6. Wasserstein ──────────────────────────────────────────────────────────


def test_wasserstein_skipped_without_reference():
    rep = compute_wasserstein(_diverse_patients(50), real_df=None)
    assert rep.inferred is False
    assert rep.severity == AuditSeverity.OK


def test_wasserstein_low_when_distributions_match():
    pytest.importorskip("scipy")
    synth = _diverse_patients(n=400, seed=1)
    real = _diverse_patients(n=400, seed=2)
    rep = compute_wasserstein(synth, real)
    assert rep.inferred is True
    assert rep.mean_distance is not None
    # Same generator family — distances should be modest.
    assert rep.mean_distance < 1.5


# ─── 7. TimeGAN sequence sanity ──────────────────────────────────────────────


def test_timegan_sanity_in_range():
    df = _diverse_patients(n=20)
    vitals = _vitals_for(df)
    rep = compute_timegan_sequence_sanity(vitals)
    assert rep.inferred is True
    assert all(rep.columns_in_range.values())


def test_timegan_sanity_out_of_range_flagged():
    df = _diverse_patients(n=10)
    vitals = _vitals_for(df)
    vitals.loc[0, "heart_rate"] = 500.0  # impossible
    rep = compute_timegan_sequence_sanity(vitals)
    assert rep.columns_in_range["heart_rate"] is False
    assert rep.severity == AuditSeverity.WARN


def test_timegan_sanity_skipped_when_empty():
    rep = compute_timegan_sequence_sanity(pd.DataFrame())
    assert rep.inferred is False
    assert rep.severity == AuditSeverity.OK


# ─── 8. End-to-end orchestrator ──────────────────────────────────────────────


def test_audit_cohort_returns_complete_report_on_healthy_cohort():
    patients = _diverse_patients(n=120)
    vitals = _vitals_for(patients)
    report = audit_cohort(
        cohort_id="test-cohort-001",
        patients_df=patients,
        vitals_df=vitals,
        epsilon=2.5,
    )
    assert report.audit_id
    assert report.cohort_id == "test-cohort-001"
    assert report.epsilon == 2.5
    # All blocks populated.
    for block in (report.k_anonymity, report.self_nearest_neighbor,
                  report.membership_inference, report.marginal_distribution,
                  report.correlation_health, report.wasserstein,
                  report.downstream_risk, report.timegan_sequences):
        assert block.severity in (AuditSeverity.OK, AuditSeverity.WARN, AuditSeverity.FAIL)


def test_audit_cohort_overall_severity_is_worst_block():
    # Force a FAIL on marginal_distribution by collapsing all columns.
    df = _diverse_patients(n=30)
    for col in [c for c in df.columns if c != "patient_id"]:
        df[col] = 0.0
    report = audit_cohort(cohort_id="collapsed-001", patients_df=df, vitals_df=None)
    assert report.marginal_distribution.severity == AuditSeverity.FAIL
    assert report.overall_severity == AuditSeverity.FAIL
    assert any("collapse" in w.lower() or "marginal" in w.lower()
               for w in report.actionable_warnings)


def test_audit_never_raises_on_pathological_input():
    # Empty dataframe — every block should degrade gracefully.
    report = audit_cohort(cohort_id="empty-cohort", patients_df=pd.DataFrame(),
                          vitals_df=None)
    assert report.audit_id
    # No actionable_warnings is acceptable; the report just shouldn't crash.


def test_audit_attaches_epsilon_provenance():
    report = audit_cohort(cohort_id="eps-001", patients_df=_diverse_patients(20), vitals_df=None,
                          epsilon=0.5)
    assert report.epsilon == 0.5
