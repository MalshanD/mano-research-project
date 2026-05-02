"""
Researcher Cohort generator + persistence.

Pipeline
--------
1. Seed every RNG (Python ``random``, NumPy, Torch) so the run is
   reproducible. If the caller doesn't pass a seed, we mint one via
   ``secrets.randbits(31)`` and record it in the manifest.
2. Call the frozen CTGAN for ``num_patients`` tabular records.
3. If requested, call the frozen TimeGAN for 7-day wearable sequences
   (denormalised to real-world units).
4. Serialise:
   * ``patients.csv`` — CTGAN output, one row per patient.
   * ``vitals.csv`` — long format, one row per (patient_id, day).
   * ``cohort.jsonl`` — one JSON object per patient bundling both.
5. SHA-256 each output and write ``manifest.json``.
6. Return the manifest + public download URLs.

Cohorts live under ``MANO_RESEARCH_DIR`` (default ``data/research_cohorts``)
in a directory per cohort: ``<cohort_id>/{patients.csv,vitals.csv,cohort.jsonl,manifest.json}``.
This keeps listing cheap (``os.listdir`` over cohort root) and lets us serve
manifests to researchers without touching a database.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from lib.synthetic.ctgan_service import CTGANService
from lib.synthetic.timegan_service import TimeGANService
from schemas.synthetic.research_cohort_schema import (
    CohortFileEntry,
    CohortFormat,
    CohortGenerateRequest,
    CohortGenerateResponse,
    CohortManifest,
)

logger = logging.getLogger(__name__)

TIMEGAN_SIGNALS = ["sleep_hours", "sleep_quality", "heart_rate", "stress_level"]


# ─── Paths + URLs ─────────────────────────────────────────────────────────

def _cohort_root() -> Path:
    raw = os.environ.get("MANO_RESEARCH_DIR") or os.path.join("data", "research_cohorts")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cohort_dir(cohort_id: str) -> Path:
    return _cohort_root() / cohort_id


def _public_url(cohort_id: str, filename: str) -> str:
    return f"/api/v1/research/cohorts/{cohort_id}/download/{filename}"


# ─── Reproducibility helpers ─────────────────────────────────────────────

def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:  # pragma: no cover — torch always available in this repo
        pass


def _model_versions() -> Dict[str, str]:
    """Hash the frozen model artefacts so the manifest proves which ones ran."""
    versions: Dict[str, str] = {}
    for label, relpath in [
        ("ctgan", Path("ml_models") / "component1" / "ctgan_model_MENTAL_HEALTH_TECH.pkl"),
        ("timegan", Path("ml_models") / "component1" / "timegan_final.pth"),
    ]:
        path = Path.cwd() / relpath
        if not path.exists():
            # Try absolute fallback via module location
            alt = Path(__file__).resolve().parent.parent.parent / relpath
            if alt.exists():
                path = alt
        if path.exists():
            sha = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    sha.update(chunk)
            versions[label] = sha.hexdigest()[:16]  # truncated — full hex is huge
        else:
            versions[label] = "missing"
    return versions


def _sha256_of(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ─── Generation + persistence ────────────────────────────────────────────

def _generate_sync(request: CohortGenerateRequest, cohort_id: str) -> CohortManifest:
    """Synchronous heart of the generator. Called from an executor so the
    event loop stays responsive during CTGAN/TimeGAN inference."""

    seed = request.seed if request.seed is not None else secrets.randbits(31)
    _seed_everything(seed)

    created_at = datetime.now(timezone.utc)
    out_dir = _cohort_dir(cohort_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    warnings: List[str] = []

    # 1. CTGAN
    ctgan = CTGANService()
    if not ctgan.is_loaded():
        raise RuntimeError("CTGAN model not loaded — cannot fulfil cohort request.")
    patients_df: pd.DataFrame = ctgan.generate(num_samples=request.num_patients)
    # Normalise column names for researcher-friendly exports.
    patients_df.insert(0, "patient_id", [f"{cohort_id}-{i:04d}" for i in range(len(patients_df))])

    # 2. TimeGAN (optional)
    vitals_df: Optional[pd.DataFrame] = None
    if request.include_timegan:
        tg = TimeGANService()
        if tg.is_loaded():
            seqs = tg.generate_denormalized(num_samples=request.num_patients)  # (N, 7, 4)
            rows = []
            for i in range(seqs.shape[0]):
                patient_id = patients_df.iloc[i]["patient_id"]
                for day in range(seqs.shape[1]):
                    rows.append({
                        "patient_id": patient_id,
                        "day": day,
                        **{
                            TIMEGAN_SIGNALS[s]: float(seqs[i, day, s])
                            for s in range(seqs.shape[2])
                        },
                    })
            vitals_df = pd.DataFrame(rows)
        else:
            warnings.append("TimeGAN not loaded — vitals sequences skipped.")

    # 3. Persist in requested formats.
    files: Dict[str, CohortFileEntry] = {}
    write_csv = request.output_format in (CohortFormat.CSV, CohortFormat.BOTH)
    write_jsonl = request.output_format in (CohortFormat.JSONL, CohortFormat.BOTH)

    if write_csv:
        p_path = out_dir / "patients.csv"
        patients_df.to_csv(p_path, index=False)
        files["patients_csv"] = CohortFileEntry(
            path=str(p_path),
            size_bytes=p_path.stat().st_size,
            sha256=_sha256_of(p_path),
            row_count=len(patients_df),
        )
        if vitals_df is not None:
            v_path = out_dir / "vitals.csv"
            vitals_df.to_csv(v_path, index=False)
            files["vitals_csv"] = CohortFileEntry(
                path=str(v_path),
                size_bytes=v_path.stat().st_size,
                sha256=_sha256_of(v_path),
                row_count=len(vitals_df),
            )

    if write_jsonl:
        j_path = out_dir / "cohort.jsonl"
        with open(j_path, "w", encoding="utf-8") as f:
            for i in range(len(patients_df)):
                patient_row = patients_df.iloc[i].to_dict()
                record = {"patient": patient_row}
                if vitals_df is not None:
                    vs = vitals_df[vitals_df["patient_id"] == patient_row["patient_id"]]
                    record["vitals"] = vs.drop(columns=["patient_id"]).to_dict(orient="records")
                f.write(json.dumps(record, default=str) + "\n")
        files["cohort_jsonl"] = CohortFileEntry(
            path=str(j_path),
            size_bytes=j_path.stat().st_size,
            sha256=_sha256_of(j_path),
            row_count=len(patients_df),
        )

    # 3.5 Run the synthetic-cohort audit. MUST never raise — on internal
    # failure we degrade to "no audit attached" and add a warning to the
    # manifest. The cohort still ships; the audit is value added on top.
    audit_attached = False
    audit_overall: Optional[str] = None
    if not getattr(request, "skip_audit", False):
        try:
            from lib.synthetic.synth_audit_service import audit_cohort as _audit
            audit_report = _audit(
                cohort_id=cohort_id,
                patients_df=patients_df,
                vitals_df=vitals_df,
                epsilon=getattr(request, "epsilon", None),
            )
            a_path = out_dir / "audit.json"
            with open(a_path, "w", encoding="utf-8") as f:
                f.write(audit_report.model_dump_json(indent=2))
            files["audit_json"] = CohortFileEntry(
                path=str(a_path),
                size_bytes=a_path.stat().st_size,
                sha256=_sha256_of(a_path),
                row_count=1,
            )
            audit_attached = True
            audit_overall = audit_report.overall_severity.value
            if audit_overall == "fail":
                warnings.append(
                    "Synthetic-cohort audit returned overall_severity=FAIL — "
                    "review audit.json before sharing externally."
                )
            elif audit_overall == "warn":
                warnings.append(
                    "Synthetic-cohort audit returned overall_severity=WARN — "
                    "review audit.json before downstream use."
                )
        except Exception as exc:
            logger.warning("cohort_audit_failed", extra={
                "cohort_id": cohort_id, "error": str(exc),
            })
            warnings.append(f"Synthetic-cohort audit failed: {exc!r}")

    manifest = CohortManifest(
        cohort_id=cohort_id,
        researcher_id=request.researcher_id,
        num_patients=request.num_patients,
        include_timegan=request.include_timegan and vitals_df is not None,
        seed=seed,
        created_at=created_at,
        ctgan_columns=list(patients_df.columns),
        timegan_signals=TIMEGAN_SIGNALS if vitals_df is not None else [],
        model_versions=_model_versions(),
        files=files,
        notes=request.notes,
        warnings=warnings,
        audit_attached=audit_attached,
        audit_overall_severity=audit_overall,
    )

    # 4. Write manifest.json last so a partial failure leaves no manifest behind
    # (listing logic treats "no manifest" as "cohort not ready").
    m_path = out_dir / "manifest.json"
    with open(m_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    return manifest


# ─── Public async API ────────────────────────────────────────────────────

async def generate_cohort(request: CohortGenerateRequest) -> CohortGenerateResponse:
    cohort_id = uuid.uuid4().hex[:16]
    loop = asyncio.get_event_loop()
    manifest = await loop.run_in_executor(None, _generate_sync, request, cohort_id)

    download_urls = {
        key: _public_url(cohort_id, Path(entry.path).name)
        for key, entry in manifest.files.items()
    }
    # Always expose the manifest itself as a download for auditors.
    download_urls["manifest"] = f"/api/v1/research/cohorts/{cohort_id}"

    logger.info(
        "research_cohort_generated",
        extra={
            "cohort_id": cohort_id,
            "researcher_id": request.researcher_id,
            "num_patients": request.num_patients,
            "seed": manifest.seed,
            "files": list(manifest.files.keys()),
        },
    )
    return CohortGenerateResponse(
        cohort_id=cohort_id,
        manifest=manifest,
        download_urls=download_urls,
    )


def load_manifest(cohort_id: str) -> CohortManifest:
    """Read a cohort manifest off disk. Raises ``FileNotFoundError`` if the
    cohort doesn't exist or was deleted."""
    # Defensive — cohort_ids are 16-char hex.
    if not cohort_id.isalnum() or not (8 <= len(cohort_id) <= 64):
        raise FileNotFoundError(cohort_id)
    path = _cohort_dir(cohort_id) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return CohortManifest.model_validate_json(f.read())


def list_cohorts() -> List[CohortManifest]:
    root = _cohort_root()
    out: List[CohortManifest] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        mpath = child / "manifest.json"
        if not mpath.exists():
            continue
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                out.append(CohortManifest.model_validate_json(f.read()))
        except Exception as exc:
            logger.warning(
                "research_cohort_manifest_read_failed",
                extra={"cohort_id": child.name, "error": str(exc)},
            )
    # Newest first for UX.
    out.sort(key=lambda m: m.created_at, reverse=True)
    return out


def resolve_cohort_file(cohort_id: str, filename: str) -> Path:
    """Return an absolute path to a cohort artefact, after validating the
    requested filename is one the cohort actually produced.

    Raises ``FileNotFoundError`` if the cohort, manifest, or named file
    doesn't exist.
    """
    manifest = load_manifest(cohort_id)
    allowed = {Path(entry.path).name for entry in manifest.files.values()}
    allowed.add("manifest.json")
    if filename not in allowed:
        raise FileNotFoundError(f"{cohort_id}/{filename}")
    path = _cohort_dir(cohort_id) / filename
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path


def load_patients_dataframe(cohort_id: str) -> pd.DataFrame:
    """Used by audit / aggregate services. Reads patients.csv off disk."""
    path = _cohort_dir(cohort_id) / "patients.csv"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def load_vitals_dataframe(cohort_id: str) -> Optional[pd.DataFrame]:
    path = _cohort_dir(cohort_id) / "vitals.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)
