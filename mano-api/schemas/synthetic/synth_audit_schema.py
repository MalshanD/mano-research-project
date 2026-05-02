"""
Pydantic schemas for the Synthetic Cohort Audit.

The audit attaches a measurable, machine-readable safety report to every
synthesised cohort. Three concerns it answers:

1. **Privacy** — does any synthetic row betray its origin? (k-anonymity,
   self-nearest-neighbour outliers, optional membership-inference AUC).
2. **Quality** — does the cohort look enough like the real distribution
   to be useful for downstream research? (marginal sanity, correlation
   health, optional Wasserstein distance, downstream-LSTM risk
   distribution).
3. **Provenance** — what model versions, what seeds, what timestamps —
   so the same audit can be re-run and the evidence chain proven.

The audit report is always attached to the cohort manifest. Researchers
can read it before downloading; auditors can pull it standalone.

Numeric severity grades (``ok | warn | fail``) summarise each block so
downstream UIs can render a green/amber/red indicator without
re-interpreting the numbers.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AuditSeverity(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


# ── Privacy blocks ──────────────────────────────────────────────────────────


class KAnonymityReport(BaseModel):
    """k-anonymity over a chosen set of quasi-identifier columns.

    A row is k-anonymous when it shares its quasi-identifier tuple with
    ``k-1`` other rows. The minimum k across the cohort is what matters —
    any row with k=1 is uniquely identifiable.
    """

    quasi_identifier_columns: List[str]
    min_k: int = Field(..., ge=0, description="Smallest cluster size; k=1 is uniquely identifiable.")
    median_k: float
    fraction_unique_rows: float = Field(..., ge=0.0, le=1.0)
    fail_threshold_k: int = Field(5, description="Severity FAIL when min_k below this.")
    severity: AuditSeverity


class SelfNearestNeighborReport(BaseModel):
    """Per-row self-NN distance over the numeric columns.

    For each synth row we compute the L2 distance to its nearest *other*
    synth row. Outliers — rows further than ``outlier_distance_threshold``
    standard deviations from the mean NN distance — are flagged as
    candidate re-identification targets.
    """

    n_rows: int
    mean_nn_distance: float
    std_nn_distance: float
    min_nn_distance: float
    max_nn_distance: float
    outlier_count: int
    outlier_fraction: float = Field(..., ge=0.0, le=1.0)
    severity: AuditSeverity


class MembershipInferenceReport(BaseModel):
    """Adversarial safety net: train a classifier to distinguish real vs.
    synthetic. AUC ≤ 0.55 ≈ no leakage; AUC ≥ 0.65 ≈ measurable leakage.

    When no reference real-data sample is provided to the audit (the
    common case at deploy time), we record ``inferred=False`` and leave
    severity at OK with a note. The audit chain still passes — the
    auditor knows membership inference was *not* run.
    """

    inferred: bool
    auc: Optional[float] = None
    n_real_samples: Optional[int] = None
    n_synth_samples: Optional[int] = None
    classifier: str = "skipped"
    note: Optional[str] = None
    severity: AuditSeverity


# ── Quality blocks ──────────────────────────────────────────────────────────


class MarginalColumnStats(BaseModel):
    column: str
    mean: float
    std: float
    min_value: float
    max_value: float
    distinct_values: int
    fraction_zero: float
    fraction_nan: float


class MarginalReport(BaseModel):
    columns: List[MarginalColumnStats]
    n_columns_collapsed: int = Field(
        ...,
        description="Columns where every row holds the same value (mode collapse).",
    )
    n_columns_constant_zero: int
    severity: AuditSeverity


class CorrelationReport(BaseModel):
    """Health of the synth correlation matrix.

    We compute the absolute mean off-diagonal correlation and flag two
    failure modes:
    - mean(|corr|) ≈ 0  → features are uncorrelated, model produced
      noise
    - mean(|corr|) > 0.85 → features are over-correlated, model
      collapsed to a 1-D manifold.
    """

    n_numeric_columns: int
    mean_abs_offdiag: float
    max_abs_offdiag: float
    n_pairs_above_threshold: int
    threshold: float = 0.95
    severity: AuditSeverity


class WassersteinReport(BaseModel):
    """Per-column Wasserstein distance vs. a reference distribution."""

    inferred: bool
    columns: Dict[str, float] = Field(
        default_factory=dict,
        description="Wasserstein distance per column; absent when no reference supplied.",
    )
    mean_distance: Optional[float] = None
    note: Optional[str] = None
    severity: AuditSeverity


class DownstreamRiskReport(BaseModel):
    """Distribution of risk classes when the synth cohort is fed through
    the frozen LSTM. A cohort that lands every patient in the same risk
    class is structurally suspect.
    """

    inferred: bool
    n_patients_scored: int = 0
    risk_class_counts: Dict[str, int] = Field(default_factory=dict)
    risk_class_proportions: Dict[str, float] = Field(default_factory=dict)
    note: Optional[str] = None
    severity: AuditSeverity


class TimeGANSequenceReport(BaseModel):
    """Sanity check on TimeGAN output ranges + temporal autocorrelation."""

    inferred: bool
    n_sequences: int = 0
    columns_in_range: Dict[str, bool] = Field(default_factory=dict)
    mean_lag1_autocorr: Optional[float] = None
    note: Optional[str] = None
    severity: AuditSeverity


# ── Top-level report ────────────────────────────────────────────────────────


class SynthAuditReport(BaseModel):
    audit_id: str
    cohort_id: str
    audited_at: datetime
    audit_version: str = "1.0"

    # Privacy
    k_anonymity: KAnonymityReport
    self_nearest_neighbor: SelfNearestNeighborReport
    membership_inference: MembershipInferenceReport

    # Quality
    marginal_distribution: MarginalReport
    correlation_health: CorrelationReport
    wasserstein: WassersteinReport
    downstream_risk: DownstreamRiskReport
    timegan_sequences: TimeGANSequenceReport

    # Roll-up
    overall_severity: AuditSeverity
    summary_notes: List[str] = Field(default_factory=list)
    actionable_warnings: List[str] = Field(default_factory=list)

    # Differential-privacy provenance
    epsilon: Optional[float] = Field(
        None,
        description="Differential-privacy epsilon claimed by the generation "
                    "step. Reproduced here unmodified — the audit does not "
                    "verify epsilon (that requires a separate analysis) but "
                    "ships it on the audit record so privacy claims and "
                    "audit results travel together.",
    )
