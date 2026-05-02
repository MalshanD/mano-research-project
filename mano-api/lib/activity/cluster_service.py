"""
Runtime service for the Dynamic GMM clustering feature.

Responsibilities
----------------
1. Expose model-status metadata — the BIC/AIC sweep, selected K,
   cluster → community mapping, fit date — to the diagnostics
   endpoints. Everything sourced from ``gmm_selection_metadata.json``.
2. Assign a single feature vector to a cluster. Thin wrapper around
   the existing ``gmm_predictor`` so the dynamic artifacts can be
   loaded on demand without touching the production loader.
3. Per-user cluster-transition detection — the Component 4 analogue
   of the trajectory tracker. Load the user's Response rows, assign
   each snapshot to a cluster, and collapse the sequence into
   ``ClusterTransition`` events.

Design notes
------------
* We keep this file DB-aware (uses SQLAlchemy) because it already needs
  the Response ORM. The pure selection math lives in
  ``gmm_selection.py`` and is covered by unit tests that don't touch
  sklearn or a database.
* Dynamic artifacts (``*_dynamic.pkl``, ``gmm_selection_metadata.json``)
  are loaded lazily from ``ml_models/component4/`` using a singleton.
  If the dynamic model is missing we fall back to the baseline GMM so
  this feature is non-breaking.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import joblib
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.response import Response
from model.users import User
from lib.activity.gmm_selection import (
    ClusterAssignment,
    MIN_SESSIONS_FOR_TRANSITIONS,
    detect_transitions,
    summarise_journey,
)


# ── artifact paths ─────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(os.path.dirname(_HERE))     # mano-api/
_MODEL_DIR = os.path.join(_BASE, "ml_models", "component4")

DYNAMIC_MODEL_PATH = os.path.join(_MODEL_DIR, "gmm_model_dynamic.pkl")
DYNAMIC_SCALER_PATH = os.path.join(_MODEL_DIR, "gmm_scaler_dynamic.pkl")
DYNAMIC_MAPPING_PATH = os.path.join(_MODEL_DIR, "gmm_cluster_mapping_dynamic.pkl")
DYNAMIC_METADATA_PATH = os.path.join(_MODEL_DIR, "gmm_selection_metadata.json")


# ── singleton state ────────────────────────────────────────────────────
_gmm = None
_scaler = None
_mapping = None
_metadata = None
_is_loaded = False
_is_dynamic = False


def _load() -> bool:
    """Lazily load dynamic artifacts; fall back to baseline if missing."""
    global _gmm, _scaler, _mapping, _metadata, _is_loaded, _is_dynamic
    if _is_loaded:
        return True
    try:
        if (os.path.exists(DYNAMIC_MODEL_PATH)
                and os.path.exists(DYNAMIC_SCALER_PATH)
                and os.path.exists(DYNAMIC_MAPPING_PATH)):
            _gmm = joblib.load(DYNAMIC_MODEL_PATH)
            _scaler = joblib.load(DYNAMIC_SCALER_PATH)
            _mapping = joblib.load(DYNAMIC_MAPPING_PATH)
            _is_dynamic = True
            if os.path.exists(DYNAMIC_METADATA_PATH):
                with open(DYNAMIC_METADATA_PATH, "r") as f:
                    _metadata = json.load(f)
            _is_loaded = True
            return True
        # fall back to baseline artifacts (same names, no _dynamic suffix)
        from lib.activity import gmm_predictor as GP
        if os.path.exists(GP.GMM_MODEL_PATH):
            _gmm = joblib.load(GP.GMM_MODEL_PATH)
            _scaler = joblib.load(GP.GMM_SCALER_PATH)
            _mapping = joblib.load(GP.GMM_MAPPING_PATH)
            _is_dynamic = False
            _is_loaded = True
            return True
    except Exception:
        _is_loaded = False
    return _is_loaded


def get_model_status() -> Dict:
    """
    Return the payload for GET /insights/clusters/model/status.

    When the dynamic metadata JSON is present we surface the full BIC/AIC
    sweep, selected K, and parsimony reasoning. When running on the
    legacy frozen artifacts we return a minimal payload flagging that
    the selection audit isn't available.
    """
    ok = _load()
    if not ok or _gmm is None:
        return {
            "is_loaded": False,
            "is_dynamic": False,
            "k": None,
            "communities": [],
            "selection": None,
            "fit_date": None,
        }

    communities = []
    if _mapping:
        for cid, info in _mapping.items():
            communities.append({
                "cluster_id": int(cid),
                "community_name": info.get("community_name"),
                "description": info.get("description"),
                "severity_score": info.get("severity_score"),
            })
        communities.sort(key=lambda c: (c.get("severity_score") or 0))

    payload: Dict = {
        "is_loaded": True,
        "is_dynamic": _is_dynamic,
        "k": int(getattr(_gmm, "n_components", 0) or 0),
        "communities": communities,
        "selection": None,
        "fit_date": None,
    }
    if _metadata is not None:
        payload["selection"] = _metadata.get("selection")
        payload["fit_date"] = _metadata.get("fit_date")
        payload["n_features"] = _metadata.get("n_features")
        payload["sweep_range"] = _metadata.get("sweep_range")
        payload["data_source"] = _metadata.get("data_source")
    return payload


# ── cluster assignment (thin wrapper) ──────────────────────────────────
def assign_cluster(
    stress_score: float,
    anxiety_score: float,
    depression_score: float,
    body_score: float,
    behavior_score: float,
    emotional_score: float,
    social_score: float,
) -> Dict:
    """
    Return ``{community_name, description, confidence, all_probabilities,
    cluster_id, method}`` using whichever GMM is loaded (dynamic if
    available, baseline otherwise).

    Mirrors the shape of ``gmm_predictor.predict_community`` so UI
    consumers don't branch on which flavour is in use.
    """
    ok = _load()
    if not ok or _gmm is None:
        from lib.activity.gmm_predictor import predict_community
        result = predict_community(
            stress_score, anxiety_score, depression_score,
            body_score, behavior_score, emotional_score, social_score,
        )
        result["cluster_id"] = None
        return result

    features = np.array([[
        stress_score, anxiety_score, depression_score,
        body_score, behavior_score, emotional_score, social_score,
    ]], dtype=float)
    features_scaled = _scaler.transform(features)

    cluster_id = int(_gmm.predict(features_scaled)[0])
    probabilities = _gmm.predict_proba(features_scaled)[0]

    info = _mapping.get(cluster_id, {})
    community_name = info.get("community_name", f"Cluster {cluster_id}")
    description = info.get("description", "")
    confidence = float(probabilities[cluster_id])

    all_probs = {}
    for cid, cinfo in _mapping.items():
        all_probs[cinfo.get("community_name", f"Cluster {cid}")] = round(
            float(probabilities[cid]), 4,
        )

    return {
        "cluster_id": cluster_id,
        "community_name": community_name,
        "description": description,
        "confidence": round(confidence, 4),
        "all_probabilities": all_probs,
        "method": "gmm_dynamic" if _is_dynamic else "gmm_baseline",
    }


# ── per-user cluster history + transitions ─────────────────────────────
# Neutral default used for wellness dims (body / behavior / emotional /
# social) when a historical Response row doesn't carry them. These four
# columns aren't currently persisted on Response — they're computed
# per-request from 20 answers in activity_service.py and only used
# transiently for the live prediction. Until the schema catches up,
# historical transition detection falls back to this neutral value and
# flags the payload with ``wellness_imputed=True`` so the UI can caveat
# it. The 3 symptom scores (stress/anxiety/depression) are always
# required — no defaulting there.
NEUTRAL_WELLNESS_SCORE = 50.0

_REQUIRED_SYMPTOM_FIELDS = ("stress_score", "anxiety_score", "depression_score")
_WELLNESS_FIELDS = ("body_score", "behavior_score", "emotional_score", "social_score")


def _response_to_feature_vec(row: Response):
    """
    Build a 7-dim feature vector from one Response row.

    Returns a 2-tuple ``(vector_or_None, wellness_imputed)``:
      * ``vector_or_None`` — 7-float list, or None if the three required
        symptom scores are missing or non-numeric.
      * ``wellness_imputed`` — True when any of the four wellness dims
        fell back to NEUTRAL_WELLNESS_SCORE (i.e. the row predates the
        wellness-on-Response schema extension).
    """
    symptom_values = []
    for field in _REQUIRED_SYMPTOM_FIELDS:
        v = getattr(row, field, None)
        if v is None:
            return None, False
        try:
            symptom_values.append(float(v))
        except (TypeError, ValueError):
            return None, False

    wellness_values = []
    wellness_imputed = False
    for field in _WELLNESS_FIELDS:
        v = getattr(row, field, None)
        if v is None:
            wellness_imputed = True
            wellness_values.append(NEUTRAL_WELLNESS_SCORE)
            continue
        try:
            wellness_values.append(float(v))
        except (TypeError, ValueError):
            wellness_imputed = True
            wellness_values.append(NEUTRAL_WELLNESS_SCORE)

    return symptom_values + wellness_values, wellness_imputed


def get_user_cluster_history(
    db: Session, user_id: int,
) -> Dict:
    """
    Return the user's cluster journey.

    Payload:
      * ``user_id``
      * ``total_sessions`` — total Response rows we could score
      * ``skipped`` — rows dropped for missing features
      * ``assignments`` — list of ``{timestamp, cluster_id, community_name, confidence}``
      * ``transitions`` — list of ClusterTransition.to_dict()
      * ``summary`` — output of ``summarise_journey``
    """
    user_exists = db.query(User.id).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    rows = (
        db.query(Response)
        .filter(Response.user_id == user_id)
        .order_by(Response.created_at.asc(), Response.id.asc())
        .all()
    )

    ok = _load()
    if not ok or _gmm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GMM clustering model is not loaded",
        )

    assignments: List[ClusterAssignment] = []
    skipped = 0
    any_imputed = False
    serialised: List[Dict] = []
    for row in rows:
        vec, wellness_imputed = _response_to_feature_vec(row)
        if vec is None:
            skipped += 1
            continue
        ts = row.created_at
        if ts is None:
            skipped += 1
            continue
        if wellness_imputed:
            any_imputed = True
        features_scaled = _scaler.transform(np.array([vec], dtype=float))
        cluster_id = int(_gmm.predict(features_scaled)[0])
        probabilities = _gmm.predict_proba(features_scaled)[0]
        confidence = float(probabilities[cluster_id])
        info = _mapping.get(cluster_id, {})
        community = info.get("community_name", f"Cluster {cluster_id}")
        assignments.append(ClusterAssignment(
            timestamp=ts,
            cluster_id=cluster_id,
            community_name=community,
            confidence=confidence,
        ))
        serialised.append({
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "cluster_id": cluster_id,
            "community_name": community,
            "confidence": round(confidence, 4),
            "wellness_imputed": wellness_imputed,
        })

    transitions = detect_transitions(assignments)
    summary = summarise_journey(assignments)

    return {
        "user_id": user_id,
        "total_sessions": len(assignments),
        "skipped": skipped,
        "assignments": serialised,
        "transitions": [t.to_dict() for t in transitions],
        "summary": summary,
        "is_dynamic_model": _is_dynamic,
        "low_confidence": len(assignments) < MIN_SESSIONS_FOR_TRANSITIONS,
        "wellness_imputed_any": any_imputed,
    }


def is_loaded() -> bool:
    return _load() and _gmm is not None


def is_dynamic() -> bool:
    _load()
    return _is_dynamic
