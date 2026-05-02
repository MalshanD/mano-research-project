"""
GMM Community Clustering Predictor
====================================
Loads the trained GMM model and provides community assignment
based on a user's 7-dimensional mental health profile.

Replaces the old rule-based if/else threshold logic with
ML-based Gaussian Mixture Model clustering.

Input features (all 0-100 scale):
  - stress_score, anxiety_score, depression_score
  - body_score, behavior_score, emotional_score, social_score

Output:
  - community_name: One of [Thriving, Stable, Growing, Healing, Supported]
  - description: Community description text
  - confidence: Probability of belonging to the assigned cluster (0-1)
  - all_probabilities: Dict of probabilities for all 5 communities
"""

import os
import numpy as np
import joblib
import logging

logger = logging.getLogger(__name__)

# Paths to the trained model files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "ml_models", "component4")

GMM_MODEL_PATH = os.path.join(MODEL_DIR, "gmm_model.pkl")
GMM_SCALER_PATH = os.path.join(MODEL_DIR, "gmm_scaler.pkl")
GMM_MAPPING_PATH = os.path.join(MODEL_DIR, "gmm_cluster_mapping.pkl")

# Load models at module level (singleton pattern - loaded once when first imported)
_gmm_model = None
_gmm_scaler = None
_gmm_cluster_mapping = None
_model_loaded = False


def _load_models():
    """Load GMM model, scaler, and cluster mapping from disk."""
    global _gmm_model, _gmm_scaler, _gmm_cluster_mapping, _model_loaded

    if _model_loaded:
        return True

    try:
        if not os.path.exists(GMM_MODEL_PATH):
            logger.warning(f"GMM model not found at {GMM_MODEL_PATH}. Falling back to rule-based assignment.")
            return False

        _gmm_model = joblib.load(GMM_MODEL_PATH)
        _gmm_scaler = joblib.load(GMM_SCALER_PATH)
        _gmm_cluster_mapping = joblib.load(GMM_MAPPING_PATH)
        _model_loaded = True

        logger.info("GMM clustering model loaded successfully.")
        logger.info(f"  Model: {GMM_MODEL_PATH}")
        logger.info(f"  Components: {_gmm_model.n_components}")
        logger.info(f"  Cluster mapping: {[(k, v['community_name']) for k, v in _gmm_cluster_mapping.items()]}")

        return True

    except Exception as e:
        logger.error(f"Failed to load GMM model: {e}")
        _model_loaded = False
        return False


def predict_community(
    stress_score: float,
    anxiety_score: float,
    depression_score: float,
    body_score: float,
    behavior_score: float,
    emotional_score: float,
    social_score: float
) -> dict:
    """
    Predict the community assignment for a user based on their 7 mental health scores.

    Args:
        stress_score: 0-100 (higher = more stressed)
        anxiety_score: 0-100 (higher = more anxious)
        depression_score: 0-100 (higher = more depressed)
        body_score: 0-100 (higher = healthier body)
        behavior_score: 0-100 (higher = healthier behavior)
        emotional_score: 0-100 (higher = healthier emotional state)
        social_score: 0-100 (higher = healthier social connections)

    Returns:
        dict with keys:
            - community_name: str (Thriving/Stable/Growing/Healing/Supported)
            - description: str
            - confidence: float (0-1)
            - all_probabilities: dict mapping community names to probabilities
            - method: str ("gmm" or "rule_based")
    """

    # Try to load models if not already loaded
    if not _load_models():
        # Fallback to rule-based assignment
        return _rule_based_fallback(
            stress_score, anxiety_score, depression_score,
            body_score, behavior_score, emotional_score, social_score
        )

    try:
        # Prepare input features as numpy array
        features = np.array([[
            stress_score, anxiety_score, depression_score,
            body_score, behavior_score, emotional_score, social_score
        ]])

        # Scale features using the trained scaler
        features_scaled = _gmm_scaler.transform(features)

        # Predict cluster
        cluster_id = _gmm_model.predict(features_scaled)[0]

        # Get probabilities for all clusters
        probabilities = _gmm_model.predict_proba(features_scaled)[0]

        # Map cluster ID to community info
        community_info = _gmm_cluster_mapping[cluster_id]
        community_name = community_info['community_name']
        description = community_info['description']
        confidence = float(probabilities[cluster_id])

        # Build probability dict for all communities
        all_probabilities = {}
        for cid, info in _gmm_cluster_mapping.items():
            all_probabilities[info['community_name']] = round(float(probabilities[cid]), 4)

        logger.info(
            f"GMM prediction: user scores=[{stress_score:.1f}, {anxiety_score:.1f}, "
            f"{depression_score:.1f}, {body_score:.1f}, {behavior_score:.1f}, "
            f"{emotional_score:.1f}, {social_score:.1f}] → {community_name} "
            f"(confidence={confidence:.2%})"
        )

        return {
            "community_name": community_name,
            "description": description,
            "confidence": round(confidence, 4),
            "all_probabilities": all_probabilities,
            "method": "gmm"
        }

    except Exception as e:
        logger.error(f"GMM prediction failed: {e}. Falling back to rule-based assignment.")
        return _rule_based_fallback(
            stress_score, anxiety_score, depression_score,
            body_score, behavior_score, emotional_score, social_score
        )


# def _rule_based_fallback(
#     stress_score, anxiety_score, depression_score,
#     body_score, behavior_score, emotional_score, social_score
# ) -> dict:
#     """
#     Original rule-based community assignment as a fallback.
#     Used only if the GMM model fails to load or predict.
#     """
#     # Calculate severity similar to the old logic
#     # Normalize scores to 0-10 scale for backward compatibility
#     max_symptom = max(stress_score, anxiety_score, depression_score)
#     max_level = max_symptom / 10.0  # Convert 0-100 to 0-10

#     if max_level >= 9.0:
#         comm_name = "Supported"
#         desc = "For individuals needing strong support and guidance."
#     elif max_level >= 7.0:
#         comm_name = "Healing"
#         desc = "For individuals focusing on recovery and active healing."
#     elif max_level >= 5.0:
#         comm_name = "Growing"
#         desc = "For individuals actively building resilience and growing."
#     elif max_level >= 3.0:
#         comm_name = "Stable"
#         desc = "For individuals maintaining their stability and wellness."
#     else:
#         comm_name = "Thriving"
#         desc = "For individuals reaching advanced wellness and thriving."

#     logger.warning(f"Using rule-based fallback: max_level={max_level:.1f} → {comm_name}")

#     return {
#         "community_name": comm_name,
#         "description": desc,
#         "confidence": 1.0,
#         "all_probabilities": {comm_name: 1.0},
#         "method": "rule_based"
#     }


def is_model_loaded() -> bool:
    """Check if the GMM model is loaded and ready."""
    return _model_loaded
