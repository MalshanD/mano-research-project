"""
Component 2 — Risk Prediction Predictor (Enhanced)

Enhancements (all ADDITIVE — the Keras Dense NN model is UNTOUCHED):
  1. FIX: Silent encoding fallback — was silently defaulting unknown categorical
     values to 0, which corrupts predictions. Now raises a clear ValueError
     with the unknown value and valid options.
  2. NEW: SHAP explainability — mathematically calculates each feature's
     contribution to the prediction using SHAP's KernelExplainer.
  3. NEW: Resource routing — appends contextual mental health resources
     based on specific score thresholds and feature combinations.
  4. NEW: Counterfactual engine — simulates what-if scenarios by tweaking
     actionable features to find the optimal path to reduce risk scores.
  5. NEW: Probability calibration (temperature scaling / isotonic) — raw
     Keras softmax is routed through ``lib/assesment/calibrator`` per head
     before any downstream consumer sees it. When ``calibration.json`` is
     absent the calibrator is identity, so this is behaviourally transparent
     in dev/test and becomes active the moment fitted parameters are loaded.

Core model preserved:
  ✓ TensorFlow/Keras Dense NN (16 features → stress/anxiety/depression 0-100)
  ✓ 832KB model file (model.keras)
  ✓ Score formula: (prob_moderate × 50) + (prob_high × 100)
  ✓ Scaler and label encoders unchanged
"""

import pandas as pd
import numpy as np
import os
import logging
from typing import Dict

# Force CPU-only execution — prevents PTX/GPU JIT compilation failure
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf

# Confirm no GPUs are used
tf.config.set_visible_devices([], 'GPU')

import joblib

from lib.assesment.calibrator import default_service as _calibration_service
from lib.assesment.uncertainty import (
    UncertaintyResult,
    aggregate_mc_samples,
    build_keras_predictors,
    input_perturbation_samples,
    is_degenerate,
    keras_has_dropout,
    mc_dropout_samples,
    METHOD_DEGENERATE,
    METHOD_INPUT_PERTURBATION,
    METHOD_MC_DROPOUT,
)

logger = logging.getLogger("component2.predictor")

MODEL_PATH = "ml_models/component2/model.keras"
SCALER_PATH = "ml_models/component2/3-class-scaler.pkl"
ENCODERS_PATH = "ml_models/component2/3-class-encoders.pkl"

if os.path.exists(MODEL_PATH):
    model = tf.keras.models.load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    encoders = joblib.load(ENCODERS_PATH)
else:
    model, scaler, encoders = None, None, None


FEATURE_COLUMNS = [
    "Age", "Gender", "Education_Level", "Employment_Status",
    "Sleep_Hours", "Physical_Activity_Hrs", "Social_Support_Score",
    "Family_History_Mental_Illness", "Chronic_Illnesses",
    "Therapy", "Meditation", "Financial_Stress", "Work_Stress",
    "Self_Esteem_Score", "Life_Satisfaction_Score", "Loneliness_Score",
]

# Head order — mirrors the 3 Keras output tensors and the calibrator
# contract. Defined at module scope so uncertainty helpers can reference
# it without forward-declaration gymnastics.
HEADS = ("stress", "anxiety", "depression")

# ── Feature classification for counterfactual engine ──────────────────────────
IMMUTABLE_FEATURES = {"Age", "Gender", "Family_History_Mental_Illness", "Chronic_Illnesses"}
ACTIONABLE_FEATURES = {
    "Sleep_Hours": {"min": 4.0, "max": 9.0, "step": 0.5, "direction": "increase"},
    "Physical_Activity_Hrs": {"min": 0.0, "max": 5.0, "step": 0.5, "direction": "increase"},
    "Social_Support_Score": {"min": 1, "max": 10, "step": 1, "direction": "increase"},
    "Meditation": {"values": ["Yes", "No"], "direction": "Yes"},
    "Therapy": {"values": ["Yes", "No"], "direction": "Yes"},
    "Financial_Stress": {"min": 1, "max": 10, "step": -1, "direction": "decrease"},
    "Work_Stress": {"min": 1, "max": 10, "step": -1, "direction": "decrease"},
    "Self_Esteem_Score": {"min": 1, "max": 10, "step": 1, "direction": "increase"},
    "Life_Satisfaction_Score": {"min": 1, "max": 10, "step": 1, "direction": "increase"},
    "Loneliness_Score": {"min": 1, "max": 10, "step": -1, "direction": "decrease"},
}

# ── Resource routing database ─────────────────────────────────────────────────
RESOURCE_DATABASE = {
    "financial_stress_high": {
        "title": "Financial Stress Support",
        "resources": [
            {"name": "SLIIT Student Counseling", "type": "counseling", "url": "https://www.sliit.lk/student-support/"},
            {"name": "Financial Planning Toolkit", "type": "self-help", "url": "https://www.consumer.gov/managing-your-money"},
        ],
        "condition": lambda data, scores: data.get("Financial_Stress", 0) >= 8 and scores.get("anxiety", {}).get("score", 0) > 60,
    },
    "crisis_intervention": {
        "title": "Crisis Support Resources",
        "resources": [
            {"name": "Sri Lanka Sumithrayo Hotline", "phone": "1393", "type": "crisis"},
            {"name": "988 Suicide & Crisis Lifeline (US)", "phone": "988", "type": "crisis"},
            {"name": "Crisis Text Line", "text": "HOME to 741741", "type": "crisis"},
        ],
        "condition": lambda data, scores: scores.get("depression", {}).get("score", 0) > 85,
    },
    "sleep_support": {
        "title": "Sleep Improvement Resources",
        "resources": [
            {"name": "CBT-i Sleep Training Guide", "type": "self-help"},
            {"name": "Sleep Hygiene Checklist", "type": "educational"},
        ],
        "condition": lambda data, scores: data.get("Sleep_Hours", 8) < 5 and scores.get("stress", {}).get("score", 0) > 50,
    },
    "social_isolation": {
        "title": "Social Connection Support",
        "resources": [
            {"name": "Community Wellness Groups", "type": "community"},
            {"name": "Peer Support Networks", "type": "peer-support"},
        ],
        "condition": lambda data, scores: data.get("Loneliness_Score", 0) >= 8 and data.get("Social_Support_Score", 10) <= 3,
    },
}


def _get_score(probs):
    """Score formula: (prob_moderate × 50) + (prob_high × 100) — PRESERVED.

    Accepts either shape (1, C) (legacy — raw Keras output) or (C,) (after
    calibration squeezes the batch axis). Both forms are treated uniformly
    so calibrator-aware callers don't need to re-expand.
    """
    arr = np.asarray(probs, dtype=float)
    if arr.ndim == 2:
        arr = arr[0]
    score = (arr[1] * 50.0) + (arr[2] * 100.0)
    return float(min(round(score, 1), 100.0))


def _get_label(score):
    """Risk label thresholds — PRESERVED"""
    if score < 35:
        return "Low"
    elif score < 70:
        return "Moderate"
    return "High"


def _calibrate_head(raw_probs: np.ndarray, head: str) -> np.ndarray:
    """Route one head's raw softmax through the CalibrationService.

    Graceful-degradation: any error inside the calibrator (missing file,
    bad params, shape mismatch) logs a warning and returns the raw probs.
    We never want a calibration bug to take the whole risk endpoint down.
    """
    try:
        arr = np.asarray(raw_probs, dtype=float)
        if arr.ndim == 2:
            arr = arr[0]
        return _calibration_service().calibrate(arr, head)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("calibration failed for head=%s: %s — using raw probs", head, exc)
        arr = np.asarray(raw_probs, dtype=float)
        return arr[0] if arr.ndim == 2 else arr


def _encode_dataframe(data: dict) -> pd.DataFrame:
    """
    Encode categorical features with PROPER error handling.

    FIX: The original code silently defaulted unknown values to 0,
    which corrupts the model's internal representation. A value of 0
    might map to an entirely different category (e.g., 'Female' instead
    of 'Male'), producing dangerously wrong risk predictions.

    Now: raises ValueError with a clear message listing valid options.
    """
    df = pd.DataFrame([data])

    encoding_warnings = []

    for col, le in encoders.items():
        if col in df.columns:
            val = str(df[col].iloc[0])
            if val in le.classes_:
                df[col] = le.transform([val])
            else:
                # FIX: Instead of silently using 0, raise a clear error
                valid_options = list(le.classes_)
                error_msg = (
                    f"Unknown value '{val}' for feature '{col}'. "
                    f"Valid options: {valid_options}"
                )
                encoding_warnings.append(error_msg)
                logger.warning(f"encoding_fallback_blocked: {error_msg}")
                raise ValueError(error_msg)

    return df


def predict(data: dict):
    """
    Run prediction using the PRESERVED Keras Dense NN.

    Enhanced with proper encoding validation AND calibration: the raw
    softmax from each head (stress / anxiety / depression) is routed
    through the CalibrationService before scoring. When no
    ``calibration.json`` is present the service is identity, so the
    output is numerically identical to the legacy behaviour until a
    calibration is fitted.
    """
    df = _encode_dataframe(data)

    scaled = scaler.transform(df[FEATURE_COLUMNS])
    preds = model.predict(scaled, verbose=0)

    # preds is a list of 3 arrays, each shape (1, 3) — one per head.
    raw_stress, raw_anxiety, raw_depression = preds[0], preds[1], preds[2]

    cal_stress = _calibrate_head(raw_stress, "stress")
    cal_anxiety = _calibrate_head(raw_anxiety, "anxiety")
    cal_depression = _calibrate_head(raw_depression, "depression")

    stress_score = _get_score(cal_stress)
    anxiety_score = _get_score(cal_anxiety)
    depression_score = _get_score(cal_depression)

    return {
        "stress": {
            "score": stress_score,
            "risk_level": _get_label(stress_score),
            "probabilities": [float(p) for p in cal_stress],
            "raw_probabilities": [float(p) for p in np.asarray(raw_stress).reshape(-1)],
        },
        "anxiety": {
            "score": anxiety_score,
            "risk_level": _get_label(anxiety_score),
            "probabilities": [float(p) for p in cal_anxiety],
            "raw_probabilities": [float(p) for p in np.asarray(raw_anxiety).reshape(-1)],
        },
        "depression": {
            "score": depression_score,
            "risk_level": _get_label(depression_score),
            "probabilities": [float(p) for p in cal_depression],
            "raw_probabilities": [float(p) for p in np.asarray(raw_depression).reshape(-1)],
        },
    }


# ── Uncertainty helpers (MC-Dropout / input-perturbation) ────────────────────

# Default MC-sample count. 30 is the Gal & Ghahramani sweet spot and matches
# Component 1's uncertainty_service. Can be overridden per-call.
DEFAULT_N_UNCERTAINTY_SAMPLES = 30
DEFAULT_PERTURBATION_SIGMA = 0.05


def _uncertainty_head_result(
    head: str,
    raw_samples: np.ndarray,
    raw_point_probs: np.ndarray,
    method: str,
) -> UncertaintyResult:
    """Calibrate both the MC samples and the point estimate, then aggregate.

    We calibrate the samples *before* aggregation so the entropy
    decomposition reflects the probabilities clinicians actually see.
    Without this step the uncertainty metrics would describe the raw
    Keras head — which could systematically over-state confidence in
    exactly the miscalibrated regions calibration is meant to fix.
    """
    svc = _calibration_service()
    cal_samples = np.stack(
        [np.asarray(svc.calibrate(row, head), dtype=float) for row in raw_samples],
        axis=0,
    )
    cal_point = np.asarray(svc.calibrate(raw_point_probs, head), dtype=float)

    # If the underlying sampler collapsed (no dropout + no perturbation)
    # the samples will all be equal — flag the method as degenerate so
    # callers know the MC numbers are uninformative.
    if is_degenerate(cal_samples):
        method = METHOD_DEGENERATE

    return aggregate_mc_samples(
        head=head,
        samples=cal_samples,
        method=method,
        point_probabilities=cal_point.tolist(),
    )


def predict_with_uncertainty(
    data: dict,
    n_samples: int = DEFAULT_N_UNCERTAINTY_SAMPLES,
    sigma: float = DEFAULT_PERTURBATION_SIGMA,
) -> dict:
    """Run the predictor with per-head Bayesian uncertainty.

    Strategy
    --------
    * If the frozen Keras model has dropout layers → MC-Dropout (one
      sample per stochastic forward pass with ``training=True``).
    * Otherwise → input-perturbation ensemble (add ``N(0, sigma)`` noise
      to the scaled feature row, one batched forward pass of size N).

    The returned dict has the same scores/risk_level/probabilities shape
    as ``predict()`` plus a ``per_head`` uncertainty section for
    stress/anxiety/depression, and a top-level ``reliable`` flag that's
    True only when *all three* heads are reliable (a conservative
    default — one unreliable head justifies clinical review of the
    whole assessment).
    """
    if n_samples < 2:
        raise ValueError("n_samples must be >= 2 for a meaningful MC sweep")

    df = _encode_dataframe(data)
    scaled = scaler.transform(df[FEATURE_COLUMNS]).astype(np.float32)

    # 1. Point estimate — dropout OFF, same path as predict().
    deterministic_fn, stochastic_fn = build_keras_predictors(model)
    point_outputs = deterministic_fn(scaled)
    point_probs = {
        HEADS[i]: np.asarray(point_outputs[i], dtype=float)[0]
        for i in range(3)
    }

    # 2. Collect MC samples per head.
    if keras_has_dropout(model):
        method = METHOD_MC_DROPOUT
        raw_samples_per_head = mc_dropout_samples(
            dropout_predict_fn=stochastic_fn,
            scaled_row=scaled,
            n_samples=n_samples,
        )
    else:
        method = METHOD_INPUT_PERTURBATION
        logger.info(
            "Keras model has no dropout layers — using input-perturbation "
            "sampler (sigma=%.3f) for uncertainty.", sigma,
        )
        raw_samples_per_head = input_perturbation_samples(
            predict_fn=deterministic_fn,
            scaled_row=scaled,
            n_samples=n_samples,
            sigma=sigma,
        )

    # 3. Calibrate + aggregate per head.
    head_results: Dict[str, UncertaintyResult] = {}
    for i, head_name in enumerate(HEADS):
        head_results[head_name] = _uncertainty_head_result(
            head=head_name,
            raw_samples=raw_samples_per_head[i],
            raw_point_probs=point_probs[head_name],
            method=method,
        )

    # 4. Build scores (same formula as predict(), using the calibrated
    # point estimates so the numbers match /predict).
    scores = {}
    for head_name, ures in head_results.items():
        point_cal = ures.point_probabilities  # already calibrated
        score = _get_score(np.asarray(point_cal))
        scores[head_name] = {
            "score": score,
            "risk_level": _get_label(score),
            "probabilities": point_cal,
        }

    all_reliable = all(r.is_reliable for r in head_results.values())

    return {
        "scores": scores,
        "uncertainty": {
            "method": method,
            "n_samples": n_samples,
            "sigma": sigma if method == METHOD_INPUT_PERTURBATION else None,
            "reliable": all_reliable,
            "per_head": {h: r.to_dict() for h, r in head_results.items()},
        },
    }


def predict_with_insights(data: dict) -> dict:
    """
    Enhanced prediction that includes:
    1. Standard risk scores (PRESERVED model output, routed through calibration)
    2. SHAP-based feature explanations
    3. Contextual resource recommendations
    4. Overall risk tier + critical-intervention flag
    5. Calibration metadata — which method is active per head, so the
       frontend / clinician can see whether probabilities are trustworthy.
    """
    # 1. Standard prediction
    scores = predict(data)

    result = {"scores": scores}

    # 2. SHAP explanations (feature importance for THIS specific user)
    try:
        explanations = explain_prediction(data)
        if explanations:
            result["explanations"] = explanations
    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")

    # 3. Resource routing
    try:
        resources = get_resources(data, scores)
        if resources:
            result["resources"] = resources
    except Exception:
        pass

    # 4. Overall risk tier
    max_score = max(
        scores["stress"]["score"],
        scores["anxiety"]["score"],
        scores["depression"]["score"],
    )
    if max_score >= 70:
        result["risk_tier"] = "High"
    elif max_score >= 35:
        result["risk_tier"] = "Moderate"
    else:
        result["risk_tier"] = "Low"

    # 5. Critical intervention flag
    if scores["depression"]["score"] > 85:
        result["critical_flag"] = {
            "type": "critical_intervention",
            "message": "MANO noticed some heavy feelings today. Here's a resource if you need someone to talk to.",
            "hotline": "1393 (Sri Lanka) / 988 (US)",
        }

    # 6. Calibration metadata — lightweight summary so callers can tell
    # whether the probabilities they're reading have been calibrated.
    try:
        svc = _calibration_service()
        status = svc.status()
        result["calibration"] = {
            "is_fitted": bool(status.get("is_fitted", False)),
            "methods": {
                name: head.get("method", "identity")
                for name, head in status.get("heads", {}).items()
            },
        }
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("calibration status lookup failed: %s", exc)

    return result


def explain_prediction(data: dict) -> dict:
    """
    Use SHAP KernelExplainer to compute per-feature contributions.
    Returns the top 5 features driving this user's risk scores.

    SHAP is a local Python library (free, unlimited) — no API calls.
    It uses the FROZEN model (no retraining, no modification).
    """
    try:
        import shap
    except ImportError:
        logger.info("SHAP not installed — skipping explanations. pip install shap")
        return {}

    df = _encode_dataframe(data)
    scaled = scaler.transform(df[FEATURE_COLUMNS])

    # Create prediction functions that SHAP can call.
    # Runs raw Keras output through the calibrator so SHAP attributions
    # match the scores the clinician actually sees in predict_with_insights.
    svc = _calibration_service()

    def predict_stress(x):
        preds = model.predict(x, verbose=0)
        combined = []
        for i in range(len(x)):
            cal_s = svc.calibrate(np.asarray(preds[0][i], dtype=float), "stress")
            combined.append((cal_s[1] * 50.0) + (cal_s[2] * 100.0))
        return np.array(combined)

    def predict_anxiety(x):
        preds = model.predict(x, verbose=0)
        combined = []
        for i in range(len(x)):
            cal_a = svc.calibrate(np.asarray(preds[1][i], dtype=float), "anxiety")
            combined.append((cal_a[1] * 50.0) + (cal_a[2] * 100.0))
        return np.array(combined)

    def predict_depression(x):
        preds = model.predict(x, verbose=0)
        combined = []
        for i in range(len(x)):
            cal_d = svc.calibrate(np.asarray(preds[2][i], dtype=float), "depression")
            combined.append((cal_d[1] * 50.0) + (cal_d[2] * 100.0))
        return np.array(combined)

    # Use a generic background dataset (zeros = mean of StandardScaler) for KernelExplainer
    # This represents the "average" user. If we use the user's own data as background, SHAP values are all 0.
    background_data = np.zeros((1, len(FEATURE_COLUMNS)))

    explanations = {}
    try:
        # Explainer for stress
        explainer_s = shap.KernelExplainer(predict_stress, background_data)
        shap_vals_s = explainer_s.shap_values(scaled, nsamples=100)
        
        # Explainer for anxiety
        explainer_a = shap.KernelExplainer(predict_anxiety, background_data)
        shap_vals_a = explainer_a.shap_values(scaled, nsamples=100)
        
        # Explainer for depression
        explainer_d = shap.KernelExplainer(predict_depression, background_data)
        shap_vals_d = explainer_d.shap_values(scaled, nsamples=100)

        # Build feature importance list for each dimension
        for dim, shap_vals in zip(["stress", "anxiety", "depression"], [shap_vals_s, shap_vals_a, shap_vals_d]):
            # shap_vals is (1, 16) for a single user
            vals = shap_vals[0] if len(shap_vals.shape) == 2 else shap_vals
            
            # Pair each feature with its SHAP value
            feature_impacts = list(zip(FEATURE_COLUMNS, vals))
            # Sort by absolute impact
            feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)

            top_features = []
            for feat_name, impact in feature_impacts[:5]:
                direction = "increases" if impact > 0 else "decreases"
                top_features.append({
                    "feature": feat_name,
                    "impact": round(float(impact), 2),
                    "direction": direction,
                    "description": _human_readable_explanation(feat_name, impact, data),
                })

            explanations[dim] = top_features

        return explanations

    except Exception as e:
        logger.warning(f"SHAP computation failed: {e}")
        return {}


def _human_readable_explanation(feature: str, impact: float, data: dict) -> str:
    """Generate plain-English explanation for a SHAP feature contribution."""
    value = data.get(feature, "N/A")
    direction = "increasing" if impact > 0 else "reducing"

    readable_map = {
        "Sleep_Hours": f"Your sleep ({value} hrs/night) is {direction} your risk",
        "Physical_Activity_Hrs": f"Your activity level ({value} hrs/week) is {direction} your risk",
        "Social_Support_Score": f"Your social support ({value}/10) is {direction} your risk",
        "Financial_Stress": f"Your financial stress ({value}/10) is {direction} your risk",
        "Work_Stress": f"Your work stress ({value}/10) is {direction} your risk",
        "Self_Esteem_Score": f"Your self-esteem ({value}/10) is {direction} your risk",
        "Life_Satisfaction_Score": f"Your life satisfaction ({value}/10) is {direction} your risk",
        "Loneliness_Score": f"Your loneliness score ({value}/10) is {direction} your risk",
        "Meditation": f"{'Practicing' if value == 'Yes' else 'Not practicing'} meditation is {direction} your risk",
        "Therapy": f"{'Attending' if value == 'Yes' else 'Not attending'} therapy is {direction} your risk",
    }
    return readable_map.get(feature, f"{feature} ({value}) is {direction} your risk level")


def get_resources(data: dict, scores: dict) -> list:
    """
    Post-processing resource routing engine.
    Maps prediction outputs + feature values to contextual mental health resources.
    """
    matched_resources = []

    for key, resource_group in RESOURCE_DATABASE.items():
        try:
            if resource_group["condition"](data, scores):
                matched_resources.append({
                    "category": key,
                    "title": resource_group["title"],
                    "resources": resource_group["resources"],
                })
        except Exception:
            continue

    return matched_resources


def generate_counterfactuals(data: dict, target_reduction: float = 5.0) -> list:
    """
    Counterfactual Engine — Prescriptive Analytics.

    Simulates tweaking each actionable feature to find which changes
    would reduce risk scores by at least `target_reduction` points.

    Architecture: Decoupled from the primary prediction pipeline.
    Only triggered for users with elevated risk (Moderate or High).
    Uses the FROZEN model — no retraining.

    Returns a list of recommended changes sorted by impact.
    """
    # Get baseline prediction
    baseline_scores = predict(data)
    baseline_avg = (
        baseline_scores["stress"]["score"]
        + baseline_scores["anxiety"]["score"]
        + baseline_scores["depression"]["score"]
    ) / 3.0

    recommendations = []

    for feature, config in ACTIONABLE_FEATURES.items():
        if feature not in data:
            continue

        original_value = data[feature]
        modified_data = data.copy()

        # Determine the target value based on direction
        if "values" in config:
            # Binary feature (e.g., Meditation: Yes/No)
            target_value = config["direction"]
            if str(original_value) == str(target_value):
                continue  # Already at optimal
            modified_data[feature] = target_value
        else:
            # Numeric feature — apply one step in the beneficial direction
            step = config["step"]
            if config["direction"] == "decrease":
                target_value = max(config["min"], float(original_value) + step)
            else:
                target_value = min(config["max"], float(original_value) + abs(step))

            if target_value == float(original_value):
                continue
            modified_data[feature] = target_value

        # Run prediction with modified feature
        try:
            modified_scores = predict(modified_data)
            modified_avg = (
                modified_scores["stress"]["score"]
                + modified_scores["anxiety"]["score"]
                + modified_scores["depression"]["score"]
            ) / 3.0

            delta = baseline_avg - modified_avg

            if delta >= target_reduction:
                recommendations.append({
                    "feature": feature,
                    "current_value": original_value,
                    "recommended_value": target_value,
                    "risk_reduction": round(delta, 1),
                    "stress_change": round(baseline_scores["stress"]["score"] - modified_scores["stress"]["score"], 1),
                    "anxiety_change": round(baseline_scores["anxiety"]["score"] - modified_scores["anxiety"]["score"], 1),
                    "depression_change": round(baseline_scores["depression"]["score"] - modified_scores["depression"]["score"], 1),
                    "description": _counterfactual_description(feature, original_value, target_value, delta),
                })
        except (ValueError, Exception):
            continue

    # Sort by largest risk reduction
    recommendations.sort(key=lambda x: x["risk_reduction"], reverse=True)
    return recommendations


def _counterfactual_description(feature: str, current, target, delta: float) -> str:
    """Generate a user-friendly recommendation description."""
    descriptions = {
        "Sleep_Hours": f"Increasing your sleep from {current} to {target} hours could reduce your risk by {delta:.0f} points",
        "Physical_Activity_Hrs": f"Increasing activity from {current} to {target} hrs/week could reduce your risk by {delta:.0f} points",
        "Social_Support_Score": f"Strengthening social connections (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
        "Financial_Stress": f"Reducing financial stress (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
        "Work_Stress": f"Reducing work stress (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
        "Meditation": f"Starting a meditation practice could reduce your risk by {delta:.0f} points",
        "Therapy": f"Starting therapy could reduce your risk by {delta:.0f} points",
        "Self_Esteem_Score": f"Improving self-esteem (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
        "Life_Satisfaction_Score": f"Improving life satisfaction (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
        "Loneliness_Score": f"Reducing loneliness (from {current} to {target}/10) could reduce your risk by {delta:.0f} points",
    }
    return descriptions.get(feature, f"Changing {feature} from {current} to {target} could help")
