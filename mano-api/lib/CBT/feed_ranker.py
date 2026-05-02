"""
PyTorch-based Feed Ranking Predictor
======================================
Loads the trained feed ranking model and provides personalized
post relevance scoring for the MANO community feed.

Singleton pattern: model loaded once at first import, reused.
Falls back to chronological ordering if model fails to load.

Usage:
    from lib.activity.feed_ranker import rank_feed_posts, is_model_loaded

    ranked_posts = rank_feed_posts(
        posts=[...],  # list of post dicts from DB
        user_scores={  # user's mental health profile
            'stress_score': 80, 'anxiety_score': 70, ...
        },
        relevance_weight=0.7  # 0.7 relevance + 0.3 recency
    )
"""

import os
import json
import pickle
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing PyTorch
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not installed. Feed ranking will use chronological ordering.")
    TORCH_AVAILABLE = False


# ============================================================
# MODEL DEFINITION (must match train_model.py exactly)
# ============================================================
if TORCH_AVAILABLE:
    class FeedRankingNet(nn.Module):
        def __init__(self, input_dim=23):
            super(FeedRankingNet, self).__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, 96),
                nn.BatchNorm1d(96),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(96, 48),
                nn.BatchNorm1d(48),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(48, 24),
                nn.BatchNorm1d(24),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(24, 1),
                nn.Sigmoid()
            )

        def forward(self, x):
            return self.network(x).squeeze(-1)


# ============================================================
# CONSTANTS
# ============================================================
POST_TYPES = ['reflect', 'milestone', 'tip', 'discussion', 'support']

# ============================================================
# SINGLETON MODEL LOADING
# ============================================================
_model = None
_scaler = None
_text_config = None
_model_loaded = False

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         'ml_models', 'component4')


def _load_model():
    """Load the feed ranking model, scaler, and text config (singleton)."""
    global _model, _scaler, _text_config, _model_loaded

    if not TORCH_AVAILABLE:
        return

    model_path = os.path.join(MODEL_DIR, 'feed_ranking_model.pt')
    scaler_path = os.path.join(MODEL_DIR, 'feed_ranking_scaler.pkl')
    config_path = os.path.join(MODEL_DIR, 'text_feature_config.json')

    try:
        if not os.path.exists(model_path):
            logger.warning(f"Feed ranking model not found: {model_path}")
            return

        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        input_dim = checkpoint.get('input_dim', 23)
        _model = FeedRankingNet(input_dim=input_dim)
        _model.load_state_dict(checkpoint['model_state_dict'])
        _model.eval()

        if not os.path.exists(scaler_path):
            logger.warning(f"Feed ranking scaler not found: {scaler_path}")
            _model = None
            return

        with open(scaler_path, 'rb') as f:
            _scaler = pickle.load(f)

        if not os.path.exists(config_path):
            logger.warning(f"Text feature config not found: {config_path}")
            _model = None
            _scaler = None
            return

        with open(config_path, 'r') as f:
            _text_config = json.load(f)

        _model_loaded = True
        logger.info(f"Feed ranking model loaded (architecture: {checkpoint.get('architecture', 'unknown')}, "
                    f"R²: {checkpoint.get('test_r2', 'N/A')})")

    except Exception as e:
        logger.error(f"Failed to load feed ranking model: {e}")
        _model = None
        _scaler = None
        _text_config = None
        _model_loaded = False


# Load on import
_load_model()


# ============================================================
# TEXT FEATURE EXTRACTION
# ============================================================
def _extract_text_features(text: str) -> list:
    """
    Extract 10 text features from post text using keyword dictionaries.
    Must match the feature extraction in generate_data.py.
    """
    if not _text_config:
        return [0.0] * 10

    text_lower = text.lower() if text else ""
    words = text_lower.split()
    word_count = len(words)

    if word_count == 0:
        return [0.0] * 10

    features = []

    # 7 topic densities
    keyword_dicts = _text_config.get('keyword_dictionaries', {})
    for topic in ['stress', 'anxiety', 'depression', 'wellness', 'social', 'emotional', 'coping']:
        keywords = keyword_dicts.get(topic, [])
        matches = sum(1 for kw in keywords if kw in text_lower)
        density = min(matches / max(word_count, 1), 1.0)
        features.append(density)

    # Positive sentiment density
    positive_words = _text_config.get('positive_words', [])
    pos_count = sum(1 for w in positive_words if w in text_lower)
    features.append(min(pos_count / max(word_count, 1), 1.0))

    # Negative sentiment density
    negative_words = _text_config.get('negative_words', [])
    neg_count = sum(1 for w in negative_words if w in text_lower)
    features.append(min(neg_count / max(word_count, 1), 1.0))

    # Normalized word count
    features.append(min(word_count / 200.0, 1.0))

    return features


def _compute_recency(created_at_str: str) -> float:
    """Compute recency score (0-1) where 1 = very recent."""
    try:
        if isinstance(created_at_str, str):
            # Handle ISO format strings
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        elif isinstance(created_at_str, datetime):
            created_at = created_at_str
        else:
            return 0.5  # Default mid-recency

        now = datetime.now()
        if created_at.tzinfo:
            created_at = created_at.replace(tzinfo=None)

        age_hours = (now - created_at).total_seconds() / 3600.0

        # Decay: 1.0 for very recent, approaching 0 for very old
        # Half-life of ~48 hours
        recency = np.exp(-age_hours / 48.0)
        return float(np.clip(recency, 0.0, 1.0))

    except Exception:
        return 0.5


# ============================================================
# PUBLIC API
# ============================================================
def is_model_loaded() -> bool:
    """Check if the feed ranking model loaded successfully."""
    return _model_loaded


def rank_feed_posts(
    posts: list,
    user_scores: dict,
    relevance_weight: float = 0.7,
    *,
    with_uncertainty: bool = False,
    n_mc_samples: int = 20,
    exploration_rate: float = 0.0,
    exploration_top_n: int = 20,
    with_explanations: bool = False,
    explanation_top_k: int = 3,
) -> list:
    """
    Rank community feed posts by personalized relevance.

    Args:
        posts: list of post dicts from DB query. Each must have:
            - 'paragraph' (str): post text
            - 'post_type' (str): one of reflect/milestone/tip/discussion/support
            - 'created_at' (str): ISO timestamp
            - Plus any other fields (passed through unchanged)
        user_scores: dict with user's mental health profile:
            - stress_score, anxiety_score, depression_score (0-100)
            - body_score, behavior_score, emotional_score, social_score (0-100)
        relevance_weight: float 0-1, how much to weight ML relevance vs recency
            (default 0.7 = 70% relevance, 30% recency)
        with_uncertainty: when True, run MC-Dropout (``n_mc_samples`` forward
            passes with dropout active) and attach an ``uncertainty`` dict to
            each post with mean / std / 95% CI / high-uncertainty flag. The
            ``relevance_score`` becomes the MC mean (more calibrated than a
            single dropout-off sample) and posts tagged as high-uncertainty
            get their ranking score blended toward recency so we don't push
            unstable recommendations.
        n_mc_samples: MC-Dropout sample count (default 20, Gal/Ghahramani).

    Returns:
        Same posts list, sorted by combined score (highest first),
        with added fields: 'relevance_score', 'recency_score', 'ranking_score',
        'ranking_method', and (if ``with_uncertainty``) 'uncertainty'.
        Returns original list (chronological) if model not loaded.
    """
    if not _model_loaded or not posts:
        # Fallback: add default fields and return as-is (chronological)
        for post in posts:
            post['relevance_score'] = 0.0
            post['recency_score'] = 0.0
            post['ranking_score'] = 0.0
            post['ranking_method'] = 'chronological'
        return posts

    # Extract user profile vector
    stress = float(user_scores.get('stress_score', 50))
    anxiety = float(user_scores.get('anxiety_score', 50))
    depression = float(user_scores.get('depression_score', 50))
    body = float(user_scores.get('body_score', 50))
    behavior = float(user_scores.get('behavior_score', 50))
    emotional = float(user_scores.get('emotional_score', 50))
    social = float(user_scores.get('social_score', 50))
    user_vector = [stress, anxiety, depression, body, behavior, emotional, social]

    recency_weight = 1.0 - relevance_weight

    try:
        for post in posts:
            # Post type one-hot
            pt = post.get('post_type', 'reflect')
            if hasattr(pt, 'name'):
                pt = pt.name
            type_onehot = [1.0 if t == pt else 0.0 for t in POST_TYPES]

            # Text features
            text = post.get('paragraph', '')
            text_features = _extract_text_features(text)

            # Recency
            recency = _compute_recency(post.get('created_at', ''))

            # Build feature vector: 7 user + 5 type + 10 text + 1 recency = 23
            features = np.array(
                user_vector + type_onehot + text_features + [recency],
                dtype=np.float32
            ).reshape(1, -1)

            features_scaled = _scaler.transform(features)
            tensor_input = torch.FloatTensor(features_scaled)

            uncertainty_info = None
            if with_uncertainty:
                # MC-Dropout: sample the posterior relevance distribution.
                from lib.activity.activity_uncertainty import (
                    predict_with_uncertainty,
                )
                ests = predict_with_uncertainty(
                    _model, tensor_input, n_samples=n_mc_samples,
                )
                est = ests[0]
                relevance = est.mean
                uncertainty_info = est.to_dict()
                # High-uncertainty posts get their ranking blended toward
                # recency so the UX doesn't feel erratic. Kept as an
                # explicit multiplicative soften rather than zeroing the
                # relevance - a high-variance prediction still carries
                # SOME information.
                if est.is_high_uncertainty:
                    relevance_weight_eff = max(relevance_weight * 0.5, 0.2)
                    recency_weight_eff = 1.0 - relevance_weight_eff
                else:
                    relevance_weight_eff = relevance_weight
                    recency_weight_eff = recency_weight
            else:
                with torch.no_grad():
                    relevance = _model(tensor_input).item()
                relevance_weight_eff = relevance_weight
                recency_weight_eff = recency_weight

            # Combined ranking score
            ranking_score = (
                relevance_weight_eff * relevance + recency_weight_eff * recency
            )

            post['relevance_score'] = round(relevance, 4)
            post['recency_score'] = round(recency, 4)
            post['ranking_score'] = round(ranking_score, 4)
            post['ranking_method'] = (
                'ml_mc_dropout' if with_uncertainty else 'ml_personalized'
            )
            if uncertainty_info is not None:
                post['uncertainty'] = uncertainty_info

            # Optional per-post explainability: attach top-k feature
            # group attributions so the UI can render "why this post".
            if with_explanations:
                from lib.CBT.feed_explainer import (
                    explain_prediction,
                    is_available as _explainer_available,
                )
                if _explainer_available():
                    attributions = explain_prediction(
                        _model,
                        _scaler,
                        features.reshape(-1),
                        base_score=relevance,
                        top_k=explanation_top_k,
                    )
                    post['explanations'] = [a.to_dict() for a in attributions]

        # Sort by ranking_score descending
        posts.sort(key=lambda p: p.get('ranking_score', 0), reverse=True)

        # Filter-bubble mitigation: interleave serendipitous picks
        # into the top-N so the user isn't locked into a single topic
        # / post_type loop. Off by default (exploration_rate=0.0).
        if exploration_rate > 0.0 and len(posts) > 1:
            from lib.CBT.feed_diversity import inject_exploration
            posts = inject_exploration(
                posts,
                exploration_rate=exploration_rate,
                top_n=exploration_top_n,
            )

        return posts

    except Exception as e:
        logger.error(f"Error ranking feed posts: {e}")
        for post in posts:
            post['relevance_score'] = 0.0
            post['recency_score'] = 0.0
            post['ranking_score'] = 0.0
            post['ranking_method'] = 'chronological'
        return posts
