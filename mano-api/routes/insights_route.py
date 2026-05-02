"""
Enhanced Risk Insights API — Component 2 Enhancements

New endpoints that sit ALONGSIDE existing /response routes (no breaking changes):
  /api/v1/insights/predict                 — Enhanced prediction with SHAP + resources
  /api/v1/insights/explain/{user}          — SHAP explanation for latest assessment
  /api/v1/insights/counterfactual          — "What-If" prescriptive analytics
  /api/v1/insights/uncertainty             — Bayesian uncertainty per head
  /api/v1/insights/trajectory/{user_id}    — Risk trajectory tracking per head
  /api/v1/insights/calibration/status      — Calibration parameters + fit metadata
  /api/v1/insights/calibration/reliability — Reliability-diagram bins per head
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, List
from db.database import get_db
from lib.assesment.predictor import (
    predict_with_insights,
    predict_with_uncertainty,
    explain_prediction,
    generate_counterfactuals,
    FEATURE_COLUMNS,
    DEFAULT_N_UNCERTAINTY_SAMPLES,
    DEFAULT_PERTURBATION_SIGMA,
)
from lib.assesment.calibrator import default_service as _calibration_service, HEADS
from lib.assesment.trajectory_service import get_user_trajectory
from lib.assesment.trajectory import (
    DEFAULT_GAP_RESET_DAYS,
    DEFAULT_WINDOW_SIZE,
)

router = APIRouter(prefix="/api/v1/insights", tags=["Risk Insights & Explainability"])


class InsightRequest(BaseModel):
    """Assessment data for enhanced prediction."""
    Age: int
    Gender: str
    Education_Level: str
    Employment_Status: str
    Sleep_Hours: float
    Physical_Activity_Hrs: float
    Social_Support_Score: int
    Family_History_Mental_Illness: str
    Chronic_Illnesses: str
    Therapy: str
    Meditation: str
    Financial_Stress: int
    Work_Stress: int
    Self_Esteem_Score: int
    Life_Satisfaction_Score: int
    Loneliness_Score: int


class UncertaintyRequest(BaseModel):
    """Assessment data for Bayesian uncertainty quantification."""
    Age: int
    Gender: str
    Education_Level: str
    Employment_Status: str
    Sleep_Hours: float
    Physical_Activity_Hrs: float
    Social_Support_Score: int
    Family_History_Mental_Illness: str
    Chronic_Illnesses: str
    Therapy: str
    Meditation: str
    Financial_Stress: int
    Work_Stress: int
    Self_Esteem_Score: int
    Life_Satisfaction_Score: int
    Loneliness_Score: int
    n_samples: Optional[int] = DEFAULT_N_UNCERTAINTY_SAMPLES
    sigma: Optional[float] = DEFAULT_PERTURBATION_SIGMA


class CounterfactualRequest(BaseModel):
    """Data for counterfactual analysis."""
    Age: int
    Gender: str
    Education_Level: str
    Employment_Status: str
    Sleep_Hours: float
    Physical_Activity_Hrs: float
    Social_Support_Score: int
    Family_History_Mental_Illness: str
    Chronic_Illnesses: str
    Therapy: str
    Meditation: str
    Financial_Stress: int
    Work_Stress: int
    Self_Esteem_Score: int
    Life_Satisfaction_Score: int
    Loneliness_Score: int
    target_reduction: Optional[float] = 1.0  # Minimum risk reduction to recommend


@router.post(
    "/predict",
    summary="Enhanced risk prediction with SHAP explainability + resources",
    description=(
        "Runs the PRESERVED Keras Dense NN model, routes the raw softmax "
        "through the per-head calibration service, then layers on SHAP "
        "feature explanations, contextual resource recommendations, and "
        "critical intervention flags."
    ),
)
async def predict_with_insights_endpoint(request: InsightRequest):
    try:
        data = request.model_dump()
        result = predict_with_insights(data)
        return result
    except ValueError as e:
        # Encoding validation error (fixed silent fallback)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}",
        )


@router.post(
    "/counterfactual",
    summary="Prescriptive analytics — what changes would reduce risk?",
    description=(
        "Simulates tweaking actionable lifestyle features (sleep, exercise, stress, etc.) "
        "to find which changes would reduce risk scores by a clinically significant margin. "
        "Uses the FROZEN model — no retraining or modification."
    ),
)
async def counterfactual_endpoint(request: CounterfactualRequest):
    try:
        data = request.model_dump()
        target = data.pop("target_reduction", 5.0)
        recommendations = generate_counterfactuals(data, target_reduction=target)
        return {
            "recommendations": recommendations,
            "count": len(recommendations),
            "target_reduction": target,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Counterfactual error: {str(e)}",
        )


# ── User-specific endpoints (fetch features from DB, run pipeline) ────────────
# The /predict and /counterfactual POST endpoints above require the caller to
# supply all 16 features. These GET endpoints do the lookup for you: they pull
# the user's latest question_answers rows, reconstruct the feature dict, and
# pipe it straight into the same ML pipeline. This is what the Insights page
# should use so it analyses REAL user data, not hardcoded demo values.

def _get_user_features(db: Session, user_id: int) -> dict:
    """Reconstruct the 16-feature dict from a user's latest question_answers.

    Each QuestionAnswer row holds (question_id, answer). The Question table
    stores question_name which maps directly to the ML feature name (e.g.
    'Age', 'Gender', 'Sleep_Hours', …). Numeric answers are coerced to the
    correct Python type so the Keras scaler doesn't choke on strings.
    """
    from model.question_answers import QuestionAnswer
    from model.question import Question
    from model.users import User

    # Validate user exists
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Fetch the user's saved answers joined with question names
    rows = (
        db.query(QuestionAnswer.answer, Question.question_name)
        .join(Question, Question.id == QuestionAnswer.question_id)
        .filter(QuestionAnswer.user_id == user_id)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No assessment answers found for this user. "
                "Please complete an ML assessment first."
            ),
        )

    # Integer feature names (must be stored as int for the scaler)
    INT_FEATURES = {
        "Age", "Social_Support_Score", "Financial_Stress",
        "Work_Stress", "Self_Esteem_Score", "Life_Satisfaction_Score",
        "Loneliness_Score",
    }
    # Float features
    FLOAT_FEATURES = {"Sleep_Hours", "Physical_Activity_Hrs"}

    features: dict = {}
    for answer, question_name in rows:
        if question_name in INT_FEATURES:
            try:
                features[question_name] = int(answer)
            except (ValueError, TypeError):
                features[question_name] = answer
        elif question_name in FLOAT_FEATURES:
            try:
                features[question_name] = float(answer)
            except (ValueError, TypeError):
                features[question_name] = answer
        else:
            features[question_name] = answer

    # Verify all 16 required features are present
    missing = [f for f in FEATURE_COLUMNS if f not in features]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Incomplete assessment — missing features: {missing}. "
                "Please retake the ML assessment to capture all required fields."
            ),
        )

    return features


@router.get(
    "/predict/user/{user_id}",
    summary="Enhanced risk insights using the user's real assessment data",
    description=(
        "Fetches the user's latest ML assessment answers from the database, "
        "reconstructs the 16-feature input vector, then runs the full "
        "SHAP + calibration + resource-routing pipeline. "
        "Use this endpoint from the Insights page instead of supplying demo features."
    ),
)
async def predict_insights_for_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    try:
        features = _get_user_features(db, user_id)
        result = predict_with_insights(features)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}",
        )


@router.get(
    "/counterfactual/user/{user_id}",
    summary="Counterfactual recommendations using the user's real assessment data",
    description=(
        "Fetches the user's latest ML assessment answers from the database, "
        "reconstructs the 16-feature input vector, then runs the counterfactual "
        "engine to identify which lifestyle changes would most reduce risk scores."
    ),
)
async def counterfactual_for_user(
    user_id: int,
    target_reduction: float = 1.0,
    db: Session = Depends(get_db),
):
    try:
        features = _get_user_features(db, user_id)
        recommendations = generate_counterfactuals(features, target_reduction=target_reduction)
        return {
            "recommendations": recommendations,
            "count": len(recommendations),
            "target_reduction": target_reduction,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Counterfactual error: {str(e)}",
        )


# ── Uncertainty (MC-Dropout / input-perturbation) ────────────────────────────
# Bayesian companion to the point-estimate /predict endpoint. Gives each of
# the three heads a stability score, entropy decomposition, and a reliability
# flag so clinicians know *how sure* the model is before acting on a
# borderline score. See lib/assesment/uncertainty.py for the sampling
# strategies and the aleatoric/epistemic decomposition.

@router.post(
    "/uncertainty",
    summary="Bayesian uncertainty quantification per head",
    description=(
        "Returns MC-Dropout (if the Keras model has dropout layers) or "
        "input-perturbation uncertainty metrics for stress, anxiety, and "
        "depression heads: predictive entropy, aleatoric vs epistemic "
        "decomposition (mutual information), argmax-stability, and a "
        "reliability flag. All probabilities are routed through the "
        "calibration service before aggregation so entropy numbers match "
        "the scores shown on /predict."
    ),
)
async def uncertainty_endpoint(request: UncertaintyRequest):
    try:
        data = request.model_dump()
        n_samples = int(data.pop("n_samples", DEFAULT_N_UNCERTAINTY_SAMPLES))
        sigma = float(data.pop("sigma", DEFAULT_PERTURBATION_SIGMA))
        return predict_with_uncertainty(data, n_samples=n_samples, sigma=sigma)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Uncertainty error: {str(e)}",
        )


# ── Risk Trajectory Tracking ──────────────────────────────────────────────────
# Snapshots answer "how bad is it right now?" Trajectories answer "which way
# is it heading?" — the two questions the Component 2 model conflates. The
# headline clinical value-add here is the "Worsening in Low Range" flag:
# cases where every individual snapshot still reads "Low" but the drift is
# unmistakable, so nothing in the existing pipeline escalates. See
# lib/assesment/trajectory.py for the state classifier and projection math.

@router.get(
    "/trajectory/{user_id}",
    summary="Per-head risk trajectory with state classification + projection alerts",
    description=(
        "Returns a six-state trajectory classification (Improving, Stable, "
        "Slowly Worsening, Rapidly Worsening, Recovering, Volatile) per head, "
        "a 'worsening in Low range' projection flag, derived metrics (peak, "
        "rate-of-change, stability index, recovery speed, days-since-high), "
        "and an actionable alert string when drift is clinically meaningful. "
        "Sparse-data rules: 1 session = baseline, 2 sessions = low-confidence "
        "direction, 3+ = full analysis. History older than a configurable gap "
        "(default 42 days) is treated as a partial reset."
    ),
)
async def trajectory_endpoint(
    user_id: int,
    window_size: int = DEFAULT_WINDOW_SIZE,
    gap_reset_days: int = DEFAULT_GAP_RESET_DAYS,
    db: Session = Depends(get_db),
):
    if window_size < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="window_size must be >= 2",
        )
    if gap_reset_days < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="gap_reset_days must be >= 1",
        )
    try:
        return get_user_trajectory(
            db, user_id=user_id,
            window_size=window_size, gap_reset_days=gap_reset_days,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trajectory error: {str(e)}",
        )


# ── Calibration diagnostics ───────────────────────────────────────────────────
# These endpoints exist so clinicians, auditors, and the frontend can inspect
# *how* the risk probabilities are being transformed before they reach users.
# The calibrator is a small but clinically important post-hoc layer over the
# frozen Keras model, and opacity here would undermine trust.

@router.get(
    "/calibration/status",
    summary="Inspect calibration parameters + fit metadata",
    description=(
        "Returns the active calibration method per head (stress / anxiety / "
        "depression), fitted parameters (temperature or isotonic breakpoint "
        "arrays), fit metadata (cohort size, date, source), and the raw vs "
        "calibrated ECE / Brier metrics recorded at fit time. When no "
        "calibration.json is present the response flags is_fitted=false so "
        "callers know the identity calibrator is in effect."
    ),
)
async def calibration_status_endpoint():
    try:
        svc = _calibration_service()
        return svc.status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calibration status error: {str(e)}",
        )


@router.get(
    "/calibration/reliability",
    summary="Reliability-diagram bins per head",
    description=(
        "Surfaces the per-head reliability bins (predicted confidence vs "
        "observed accuracy) captured on the calibration cohort. Intended "
        "for the admin dashboard's reliability diagrams; consumers plot "
        "bin_lower/bin_upper on the x-axis and empirical_accuracy vs "
        "mean_confidence as the two series."
    ),
)
async def calibration_reliability_endpoint(head: Optional[str] = None):
    try:
        svc = _calibration_service()
        status_payload = svc.status()
        heads_payload = status_payload.get("heads", {})

        if head is not None:
            if head not in heads_payload:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Unknown head '{head}'. Valid heads: {list(HEADS)}",
                )

            hd = heads_payload[head]
            raw_bins = (hd.get("raw_metrics") or {}).get("reliability_bins", [])
            cal_bins = (hd.get("calibrated_metrics") or {}).get("reliability_bins", [])
            return {
                "head": head,
                "method": hd.get("method", "identity"),
                "raw_reliability_bins": raw_bins,
                "calibrated_reliability_bins": cal_bins,
            }

        out: Dict[str, Dict] = {}
        for name, hd in heads_payload.items():
            raw_bins = (hd.get("raw_metrics") or {}).get("reliability_bins", [])
            cal_bins = (hd.get("calibrated_metrics") or {}).get("reliability_bins", [])
            out[name] = {
                "method": hd.get("method", "identity"),
                "raw_reliability_bins": raw_bins,
                "calibrated_reliability_bins": cal_bins,
            }
        return {"is_fitted": status_payload.get("is_fitted", False), "heads": out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reliability diagnostics error: {str(e)}",
        )


# ── Dynamic GMM Clustering ────────────────────────────────────────────
# Component 4 historically ran a GaussianMixture with K hardcoded to 5.
# The master tech report flagged this as a known limitation. These
# endpoints surface the BIC/AIC-driven cluster-count selection, let
# callers assign a single feature vector, and expose a per-user cluster
# journey with transition events (analogous to the Component 2
# trajectory tracker). See lib/activity/gmm_selection.py for the
# selection math and lib/activity/cluster_service.py for the runtime
# adapter.

from lib.activity import cluster_service as _cluster_service  # noqa: E402


class ClusterAssignRequest(BaseModel):
    """7-dim wellness + symptom profile for a single cluster assignment."""
    stress_score: float
    anxiety_score: float
    depression_score: float
    body_score: float
    behavior_score: float
    emotional_score: float
    social_score: float


@router.get(
    "/clusters/model/status",
    summary="Dynamic GMM model status — selected K, BIC/AIC sweep, fit audit",
    description=(
        "Surfaces the BIC/AIC-driven cluster-count selection for the Component 4 "
        "community-clustering model: which K was selected, the full per-K sweep "
        "(BIC, AIC, log-likelihood, silhouette, free-parameter count), whether "
        "the parsimony rule adjusted the winner, and fit metadata (cohort size, "
        "covariance type, fit date). When only the frozen baseline (fixed K=5) "
        "is present the response flags is_dynamic=false so clients can caveat "
        "the model choice."
    ),
)
async def cluster_model_status_endpoint():
    try:
        return _cluster_service.get_model_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cluster model status error: {str(e)}",
        )


@router.post(
    "/clusters/assign",
    summary="Assign a single 7-dim profile to a GMM cluster",
    description=(
        "Thin wrapper over the loaded GaussianMixture. Returns the cluster id, "
        "community name + description, confidence (predict_proba), and the full "
        "probability distribution across all clusters. Uses the dynamic model "
        "if loaded, otherwise falls back to the baseline K=5 model."
    ),
)
async def cluster_assign_endpoint(request: ClusterAssignRequest):
    try:
        data = request.model_dump()
        return _cluster_service.assign_cluster(**data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cluster assignment error: {str(e)}",
        )


@router.get(
    "/clusters/transitions/{user_id}",
    summary="Per-user cluster journey + transition events",
    description=(
        "Loads the user's Response history oldest->newest, assigns each "
        "snapshot to a GMM cluster, and collapses consecutive same-cluster "
        "assignments into transition events (from_community -> to_community, "
        "at timestamp). Also returns a summary (current community, unique "
        "clusters visited, most common community) and flags low_confidence "
        "when the history is shorter than MIN_SESSIONS_FOR_TRANSITIONS. "
        "Note: wellness_imputed_any=true means at least one historical row "
        "was missing body/behavior/emotional/social scores and the clustering "
        "fell back to a neutral default."
    ),
)
async def cluster_transitions_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
):
    try:
        return _cluster_service.get_user_cluster_history(db, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cluster transitions error: {str(e)}",
        )


# ── CBT Multi-Distortion Detection ───────────────────────────────────
# The existing journal CBT flow returns a single argmax distortion
# label. Journal entries often contain co-occurring distortions
# (catastrophizing + mind-reading is common), so this endpoint
# reinterprets the same MLP softmax as a multi-label signal using the
# threshold + "none"-gate rules in lib/activity/cbt_multilabel.py.

from lib.CBT.cbt_predictor import analyze_journal_text_multilabel  # noqa: E402
from lib.CBT.cbt_multilabel import (  # noqa: E402
    DEFAULT_THRESHOLD as _CBT_DEFAULT_THRESHOLD,
    DEFAULT_MAX_DISTORTIONS as _CBT_DEFAULT_MAX,
)


class CbtMultilabelRequest(BaseModel):
    """Journal text + optional multi-label knobs."""
    text: str
    stress_score: Optional[int] = 50
    anxiety_score: Optional[int] = 50
    depression_score: Optional[int] = 50
    threshold: Optional[float] = _CBT_DEFAULT_THRESHOLD
    max_count: Optional[int] = _CBT_DEFAULT_MAX


@router.post(
    "/cbt/multilabel",
    summary="Multi-distortion detection for a journal entry",
    description=(
        "Runs the PRESERVED CBT MLP classifier and reinterprets the "
        "softmax as a multi-label signal: every distortion above "
        "``threshold`` is reported (subject to ``max_count``), unless "
        "the classifier's 'none' class dominates — in which case we "
        "trust the 'no distortion detected' verdict and return an empty "
        "picks list. Co-occurrence strength + a one-word UI tag "
        "(none/single/pair/cluster) are included so the frontend can "
        "pick a card layout without re-implementing the selection "
        "logic. Falls back to the keyword heuristic when the MLP is "
        "not loaded."
    ),
)
async def cbt_multilabel_endpoint(request: CbtMultilabelRequest):
    try:
        data = request.model_dump()
        text = data.pop("text", "") or ""
        threshold = data.pop("threshold", _CBT_DEFAULT_THRESHOLD)
        max_count = data.pop("max_count", _CBT_DEFAULT_MAX)
        result = analyze_journal_text_multilabel(
            text=text,
            stress_score=data.get("stress_score", 50),
            anxiety_score=data.get("anxiety_score", 50),
            depression_score=data.get("depression_score", 50),
            threshold=threshold,
            max_count=max_count,
        )
        from lib.CBT.cbt_multilabel import classify_co_occurrence, MultiLabelResult, DistortionPick
        # Re-hydrate the tag (can't call classify_co_occurrence on a
        # dict, and we don't want to leak the dataclass into the
        # route; build a transient MultiLabelResult).
        ml = result["multi_label"]
        picks_obj = [
            DistortionPick(
                distortion_type=p["distortion_type"],
                confidence=p["confidence"],
                rank=p["rank"],
            ) for p in ml["picks"]
        ]
        primary_obj = picks_obj[0] if picks_obj else None
        co_tag = classify_co_occurrence(MultiLabelResult(
            picks=picks_obj,
            is_none=ml["is_none"],
            primary=primary_obj,
            co_occurrence_strength=ml["co_occurrence_strength"],
            threshold_used=ml["threshold_used"],
            reason=ml["reason"],
            all_probabilities=ml["all_probabilities"],
        ))
        result["ui_tag"] = co_tag
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CBT multilabel error: {str(e)}",
        )


# ── CBT CALIBRATION STATUS (Component 4) ───────────────────────────────
# Surface the frozen calibrator's configuration so the frontend can
# caveat results ("these probabilities are calibrated against N=209
# held-out samples, ECE=0.002 isotonic") and ops can verify that
# cbt_calibration.json has actually been deployed alongside the model.

@router.get(
    "/cbt/calibration/status",
    summary="CBT MLP calibration status + diagnostics",
    description=(
        "Returns the currently-active CBT calibrator: method "
        "(temperature / isotonic / identity), number of calibration "
        "samples, raw-vs-calibrated ECE + Brier, and the relative ECE "
        "improvement over raw softmax. Returns ``identity`` method with "
        "``is_fitted=false`` if no calibration.json has been deployed."
    ),
)
async def cbt_calibration_status_endpoint():
    try:
        from lib.CBT.cbt_calibrator import default_service
        return default_service().status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CBT calibration status error: {str(e)}",
        )
