"""
PyTorch-based Activity Recommendation Predictor
=================================================
Loads the trained PyTorch neural network model and provides
activity relevance scoring for the MANO platform.

Singleton pattern: model is loaded once at first import and reused.
Falls back to None (signaling rule-based fallback) if model fails to load.

Usage:
    from lib.activity.recommendation_predictor import score_all_activities, is_model_loaded

    results = score_all_activities(
        stress_score=80, anxiety_score=70, depression_score=30,
        body_score=40, behavior_score=45, emotional_score=35, social_score=50,
        activities_database=ACTIVITIES_DATABASE
    )
    # Returns sorted list of {"activity": dict, "relevance_score": float, ...} or None
"""

import os
import json
import pickle
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Try importing PyTorch
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not installed. Activity recommendation will use rule-based fallback.")
    TORCH_AVAILABLE = False


# ============================================================
# MODEL DEFINITION (must match train_model.py exactly)
# ============================================================
if TORCH_AVAILABLE:
    class ActivityRecommendationNet(nn.Module):
        """Neural network for predicting activity relevance scores."""

        def __init__(self, input_dim=24):
            super(ActivityRecommendationNet, self).__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(128, 64),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 32),
                nn.BatchNorm1d(32),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(32, 1),
                nn.Sigmoid()
            )

        def forward(self, x):
            return self.network(x).squeeze(-1)


# ============================================================
# ENCODING CONSTANTS (must match generate_data.py)
# ============================================================
CATEGORIES = ['stress_relief', 'anxiety_relief', 'depression_relief', 'sleep',
              'physical', 'social', 'emotional', 'mindfulness', 'routine', 'professional']
CONDITIONS = ['stress', 'anxiety', 'depression']
DIFFICULTY_MAP = {'easy': 0.25, 'medium': 0.5, 'hard': 0.75}


# ============================================================
# SINGLETON MODEL LOADING
# ============================================================
_model = None
_scaler = None
_activity_encodings = None
_model_loaded = False

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         'ml_models', 'component4')


def _load_model():
    """Load the PyTorch model, scaler, and activity encodings (singleton)."""
    global _model, _scaler, _activity_encodings, _model_loaded

    if not TORCH_AVAILABLE:
        logger.warning("PyTorch not available. Skipping model load.")
        return

    model_path = os.path.join(MODEL_DIR, 'recommendation_model.pt')
    scaler_path = os.path.join(MODEL_DIR, 'recommendation_scaler.pkl')
    encodings_path = os.path.join(MODEL_DIR, 'activity_encodings.json')

    try:
        # Load PyTorch model
        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}")
            return

        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        input_dim = checkpoint.get('input_dim', 24)
        _model = ActivityRecommendationNet(input_dim=input_dim)
        _model.load_state_dict(checkpoint['model_state_dict'])
        _model.eval()  # Set to evaluation mode (disables dropout, uses running stats for BatchNorm)

        # Load scaler
        if not os.path.exists(scaler_path):
            logger.warning(f"Scaler file not found: {scaler_path}")
            _model = None
            return

        with open(scaler_path, 'rb') as f:
            _scaler = pickle.load(f)

        # Load activity encodings
        if not os.path.exists(encodings_path):
            logger.warning(f"Activity encodings not found: {encodings_path}")
            _model = None
            _scaler = None
            return

        with open(encodings_path, 'r') as f:
            _activity_encodings = json.load(f)

        _model_loaded = True
        logger.info(f"PyTorch recommendation model loaded successfully "
                    f"(architecture: {checkpoint.get('architecture', 'unknown')}, "
                    f"R²: {checkpoint.get('test_r2', 'N/A')})")

    except Exception as e:
        logger.error(f"Failed to load recommendation model: {e}")
        _model = None
        _scaler = None
        _activity_encodings = None
        _model_loaded = False


# Load on import
_load_model()


# ============================================================
# PUBLIC API
# ============================================================
def is_model_loaded() -> bool:
    """Check if the PyTorch recommendation model loaded successfully."""
    return _model_loaded


def _encode_activity_from_db(activity: dict) -> list:
    """
    Encode an activity from the database into a 17-dim feature vector.
    Used as fallback if the activity isn't in activity_encodings.json.
    """
    cat_vec = [1.0 if activity.get('category') == c else 0.0 for c in CATEGORIES]
    cond_vec = [1.0 if c in activity.get('target_conditions', []) else 0.0 for c in CONDITIONS]
    difficulty = DIFFICULTY_MAP.get(activity.get('difficulty', 'medium'), 0.5)
    duration = min(activity.get('duration_minutes', 15) / 60.0, 1.0)
    effectiveness = activity.get('effectiveness_score', 70) / 100.0
    scientific = 1.0 if activity.get('scientific_backing', False) else 0.0
    return cat_vec + cond_vec + [difficulty, duration, effectiveness, scientific]


def score_all_activities(
    stress_score: float,
    anxiety_score: float,
    depression_score: float,
    body_score: float,
    behavior_score: float,
    emotional_score: float,
    social_score: float,
    activities_database: list,
    *,
    with_uncertainty: bool = False,
    n_mc_samples: int = 20,
    with_cold_start_fallback: bool = True,
    diversity_lambda: float = 1.0,
    diversity_top_k: int = 20,
) -> list:
    """
    Score all activities for a user using the trained PyTorch model.

    Args:
        stress_score: 0-100 stress level
        anxiety_score: 0-100 anxiety level
        depression_score: 0-100 depression level
        body_score: 0-100 body wellness score
        behavior_score: 0-100 behavior wellness score
        emotional_score: 0-100 emotional wellness score
        social_score: 0-100 social wellness score
        activities_database: list of activity dicts from data/activities.py

    Returns:
        Sorted list of dicts with keys: activity, relevance_score, matched_conditions, matched_problems
        Returns None if model not loaded (signals fallback to rule-based).
    """
    if not _model_loaded:
        return None

    # Cold-start fallback: a user who hasn't completed onboarding has
    # all-None / all-zero scores. Feeding zeros to the MLP collapses
    # the relevance distribution, so substitute a mild-distress
    # population prior when the profile carries no signal.
    cold_start_applied = False
    if with_cold_start_fallback:
        from lib.activity.activity_diversity import prepare_user_scores
        effective, cold_start_applied = prepare_user_scores(
            {
                "stress_score": stress_score,
                "anxiety_score": anxiety_score,
                "depression_score": depression_score,
                "body_score": body_score,
                "behavior_score": behavior_score,
                "emotional_score": emotional_score,
                "social_score": social_score,
            },
            with_cold_start_fallback=True,
        )
        stress_score = float(effective["stress_score"])
        anxiety_score = float(effective["anxiety_score"])
        depression_score = float(effective["depression_score"])
        body_score = float(effective["body_score"])
        behavior_score = float(effective["behavior_score"])
        emotional_score = float(effective["emotional_score"])
        social_score = float(effective["social_score"])

    user_scores = [stress_score, anxiety_score, depression_score,
                   body_score, behavior_score, emotional_score, social_score]

    try:
        results = []

        for activity in activities_database:
            act_id = activity['id']

            # Get encoding: prefer pre-computed, fallback to on-the-fly
            if _activity_encodings and act_id in _activity_encodings:
                act_encoding = _activity_encodings[act_id]['encoding']
            else:
                act_encoding = _encode_activity_from_db(activity)

            # Build feature vector: 7 user scores + 17 activity features = 24
            features = np.array(user_scores + act_encoding, dtype=np.float32).reshape(1, -1)
            features_scaled = _scaler.transform(features)
            tensor_input = torch.FloatTensor(features_scaled)

            uncertainty_info = None
            if with_uncertainty:
                from lib.activity.activity_uncertainty import (
                    predict_with_uncertainty,
                )
                ests = predict_with_uncertainty(
                    _model, tensor_input, n_samples=n_mc_samples,
                )
                est = ests[0]
                relevance_score = est.mean
                uncertainty_info = est.to_dict()
            else:
                with torch.no_grad():
                    relevance_score = _model(tensor_input).item()

            # Determine matched conditions and problems
            matched_conditions = []
            condition_scores = {'stress': stress_score, 'anxiety': anxiety_score, 'depression': depression_score}
            for cond in activity.get('target_conditions', []):
                if condition_scores.get(cond, 0) > 30:  # threshold for "affected"
                    matched_conditions.append(cond)

            matched_problems = []
            problem_indicators = {
                'high_stress': stress_score > 60,
                'anxiety': anxiety_score > 40,
                'panic': anxiety_score > 70,
                'depression': depression_score > 40,
                'low_energy': depression_score > 50 or body_score < 40,
                'withdrawal': depression_score > 60,
                'low_motivation': depression_score > 50,
                'sleep_issues': body_score < 40 or stress_score > 60,
                'physical_health': body_score < 40,
                'poor_routine': behavior_score < 40,
                'loneliness': social_score < 40,
                'isolation': social_score < 30,
                'emotional_wellbeing': emotional_score < 40,
                'racing_thoughts': anxiety_score > 60,
                'overwhelm': stress_score > 60 or anxiety_score > 60,
            }
            for prob in activity.get('target_problems', []):
                if problem_indicators.get(prob, False):
                    matched_problems.append(prob)

            row = {
                'activity': activity,
                'relevance_score': round(relevance_score * 100, 2),  # Scale to 0-100 for consistency
                'matched_conditions': matched_conditions,
                'matched_problems': matched_problems,
            }
            if uncertainty_info is not None:
                row['uncertainty'] = uncertainty_info
            results.append(row)

        # Sort by relevance (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Optional MMR diversity pass on the head of the list — avoids
        # serving a top-10 that's entirely one category (e.g. all
        # breathing exercises). Only active when caller opts in via
        # diversity_lambda < 1.0.
        if diversity_lambda < 1.0 and len(results) > 1:
            from lib.activity.activity_diversity import mmr_rerank
            results = mmr_rerank(
                results,
                lambda_diversity=diversity_lambda,
                top_k=diversity_top_k,
            )

        # Annotate cold-start status so the caller (and the API response)
        # can distinguish "MLP recommendation on real profile" vs
        # "MLP recommendation on population prior".
        if cold_start_applied and results:
            for row in results:
                row['cold_start'] = True

        return results

    except Exception as e:
        logger.error(f"Error scoring activities with PyTorch model: {e}")
        return None
