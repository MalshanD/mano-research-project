"""
CBT Cognitive Distortion Predictor
====================================
Loads the trained MLP classifier and TF-IDF vectorizer to classify
journal text into 10 cognitive distortion types + "none" (balanced).

Singleton pattern: model loaded once at first import, reused.
Falls back to keyword-based detection if model fails to load.

Usage:
    from lib.activity.cbt_predictor import analyze_journal_text, is_model_loaded

    result = analyze_journal_text(
        text="I failed the test so my entire life is ruined",
        stress_score=70, anxiety_score=80, depression_score=40
    )
    # Returns: { distortion_type, label, confidence, severity, reframe, explanation, top3 }
"""

import os
import json
import pickle
import numpy as np
import logging
import random

logger = logging.getLogger(__name__)

# ============================================================
# LOAD MODEL ARTIFACTS (singleton)
# ============================================================
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml_models", "component4")

_clf = None
_svr = None
_tfidf = None
_le = None
_catalog = None
_model_loaded = False

try:
    clf_path = os.path.join(_MODEL_DIR, "cbt_distortion_model.pkl")
    svr_path = os.path.join(_MODEL_DIR, "cbt_severity_model.pkl")
    tfidf_path = os.path.join(_MODEL_DIR, "cbt_tfidf_vectorizer.pkl")
    le_path = os.path.join(_MODEL_DIR, "cbt_label_encoder.pkl")
    catalog_path = os.path.join(_MODEL_DIR, "distortion_catalog.json")

    if all(os.path.exists(p) for p in [clf_path, svr_path, tfidf_path, le_path, catalog_path]):
        with open(clf_path, "rb") as f:
            _clf = pickle.load(f)
        with open(svr_path, "rb") as f:
            _svr = pickle.load(f)
        with open(tfidf_path, "rb") as f:
            _tfidf = pickle.load(f)
        with open(le_path, "rb") as f:
            _le = pickle.load(f)
        with open(catalog_path, "r") as f:
            _catalog = json.load(f)
        _model_loaded = True
        logger.info("CBT distortion model loaded successfully.")
    else:
        logger.warning("CBT model files not found. Using keyword-based fallback.")
except Exception as e:
    logger.warning(f"Failed to load CBT model: {e}. Using keyword-based fallback.")


# ============================================================
# KEYWORD FALLBACK (if model not available)
# ============================================================
_KEYWORD_PATTERNS = {
    "catastrophizing": ["ruined", "worst", "disaster", "terrible", "horrible", "never recover", "life is over", "end of the world"],
    "black_and_white": ["always", "never", "completely", "totally", "either", "perfect or", "no point", "all or nothing"],
    "overgeneralization": ["nothing ever", "everyone always", "always mess", "never get", "always happens", "nobody ever"],
    "mind_reading": ["they think", "they must think", "everyone thinks", "probably thinks", "judging me", "thinks I am"],
    "fortune_telling": ["I know I will", "going to fail", "will never", "definitely going to", "it won't work", "no point trying"],
    "emotional_reasoning": ["I feel like a", "feel so.*must be", "feel stupid so", "feel worthless", "feel like.*true"],
    "should_statements": ["I should", "I must", "I have to", "I ought to", "should not feel", "should be able"],
    "labeling": ["I am a loser", "I am stupid", "I am worthless", "I am a failure", "I am terrible", "I am a fraud"],
    "personalization": ["all my fault", "because of me", "I caused", "I ruined", "blame myself", "my fault"],
    "discounting_positive": ["doesn't count", "just luck", "anyone could", "not a big deal", "doesn't matter", "not really"],
}


def is_model_loaded():
    """Check if the ML model is loaded."""
    return _model_loaded


def analyze_journal_text(text, stress_score=50, anxiety_score=50, depression_score=50):
    """
    Analyze journal text for cognitive distortions.

    Args:
        text: Journal entry text
        stress_score: User's current stress level (0-100)
        anxiety_score: User's current anxiety level (0-100)
        depression_score: User's current depression level (0-100)

    Returns:
        dict with distortion_type, label, confidence, severity, reframe, explanation, top3
    """
    if not text or len(text.strip()) < 5:
        return _build_result("none", 1.0, 0.0, stress_score, anxiety_score, depression_score)

    if _model_loaded:
        return _ml_analyze(text, stress_score, anxiety_score, depression_score)
    else:
        return _keyword_analyze(text, stress_score, anxiety_score, depression_score)


def _ml_analyze(text, stress_score, anxiety_score, depression_score):
    """ML-based analysis using trained MLP + SVR."""
    try:
        X = _tfidf.transform([text])
        X_dense = X.toarray().astype(np.float32)

        # Classification
        probs = _clf.predict_proba(X_dense)[0]
        pred_idx = np.argmax(probs)
        pred_label = _le.inverse_transform([pred_idx])[0]
        confidence = float(probs[pred_idx])

        # Severity
        severity = float(_svr.predict(X_dense)[0])
        severity = max(0.0, min(3.0, severity))

        # Top 3 predictions
        top3_idx = np.argsort(probs)[::-1][:3]
        top3 = [
            {"type": _le.inverse_transform([i])[0], "confidence": float(probs[i])}
            for i in top3_idx
        ]

        result = _build_result(pred_label, confidence, severity, stress_score, anxiety_score, depression_score)
        result["top3"] = top3
        result["method"] = "ml"
        return result

    except Exception as e:
        logger.error(f"ML analysis failed: {e}. Falling back to keywords.")
        return _keyword_analyze(text, stress_score, anxiety_score, depression_score)


def _keyword_analyze(text, stress_score, anxiety_score, depression_score):
    """Keyword-based fallback analysis."""
    text_lower = text.lower()
    best_type = "none"
    best_count = 0

    for distortion, keywords in _KEYWORD_PATTERNS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_type = distortion

    confidence = min(0.9, 0.3 + best_count * 0.15) if best_type != "none" else 0.85
    severity = min(3.0, best_count * 0.8) if best_type != "none" else 0.0

    result = _build_result(best_type, confidence, severity, stress_score, anxiety_score, depression_score)
    result["method"] = "keyword_fallback"
    return result


def _build_result(distortion_type, confidence, severity, stress_score, anxiety_score, depression_score):
    """Build the full result dict with catalog data, reframe, and context."""
    catalog_entry = (_catalog or {}).get(distortion_type, {})

    # Determine dominant condition context from user's assessment
    scores = {"stress": stress_score, "anxiety": anxiety_score, "depression": depression_score}
    condition_context = max(scores, key=scores.get)

    # Select a reframe suggestion tailored to the distortion
    reframe_templates = catalog_entry.get("reframe_templates", [])
    reframe = random.choice(reframe_templates) if reframe_templates else ""

    # Adjust reframe language based on severity
    if severity >= 2.5 and reframe:
        reframe = f"Take a gentle moment to consider: {reframe}"
    elif severity >= 1.5 and reframe:
        reframe = f"It might help to ask yourself: {reframe}"

    return {
        "distortion_type": distortion_type,
        "label": catalog_entry.get("label", distortion_type.replace("_", " ").title()),
        "description": catalog_entry.get("description", ""),
        "confidence": round(confidence, 4),
        "severity": round(severity, 2),
        "severity_label": _severity_label(severity),
        "condition_context": condition_context,
        "reframe_suggestion": reframe,
        "cbt_explanation": catalog_entry.get("cbt_explanation", ""),
        "icon": catalog_entry.get("icon", "info"),
        "color": catalog_entry.get("color", "#6B7280"),
        "is_distorted": distortion_type != "none",
        "method": "ml" if _model_loaded else "keyword_fallback",
    }


def _severity_label(severity):
    """Convert numeric severity to human label."""
    if severity < 0.5:
        return "balanced"
    elif severity < 1.5:
        return "mild"
    elif severity < 2.5:
        return "moderate"
    else:
        return "severe"


def get_distortion_catalog():
    """Return the full distortion catalog for the frontend."""
    if _catalog:
        return _catalog
    # Minimal fallback catalog
    return {dt: {"label": dt.replace("_", " ").title()} for dt in _KEYWORD_PATTERNS}


# ──────────────────────────────────────────────────────────────────────
# MULTI-DISTORTION DETECTION (Component 4 deep-dive)
# ──────────────────────────────────────────────────────────────────────
# The existing ``analyze_journal_text`` returns a single argmax label,
# which under-represents journal entries that contain co-occurring
# distortions (catastrophizing + mind-reading is a common pair). The
# wrapper below reuses the same MLP softmax output but passes it
# through ``cbt_multilabel.select_multi_distortions`` so the caller
# gets every distortion above a calibrated threshold, subject to the
# "none"-class gate and a max-count cap.
#
# Non-breaking: ``analyze_journal_text`` is untouched and still used
# by the existing journal flow. This is an opt-in second endpoint.
def analyze_journal_text_multilabel(
    text,
    stress_score=50,
    anxiety_score=50,
    depression_score=50,
    threshold=None,
    max_count=None,
):
    """
    Return a multi-label distortion result for a single journal entry.

    Shape:
      {
        "text": str,
        "method": "ml" | "keyword_fallback" | "empty",
        "multi_label": MultiLabelResult.to_dict(),
        "context": {stress/anxiety/depression scores},
        "catalog": {...per-distortion catalog entries for each pick...},
      }

    Args:
        text: journal text (same contract as ``analyze_journal_text``).
        threshold: per-class min prob; defaults to
            ``cbt_multilabel.DEFAULT_THRESHOLD`` (0.20).
        max_count: max distortions reported; defaults to 3.
    """
    from lib.CBT.cbt_multilabel import (
        select_multi_distortions,
        DEFAULT_THRESHOLD,
        DEFAULT_MAX_DISTORTIONS,
        NONE_CLASS_NAME,
    )
    from lib.CBT.cbt_calibrator import default_service as _cbt_calibrator

    t = (text or "").strip()
    threshold = float(threshold) if threshold is not None else DEFAULT_THRESHOLD
    max_count = int(max_count) if max_count is not None else DEFAULT_MAX_DISTORTIONS

    # Handle the trivially-short case the same way analyze_journal_text does
    if len(t) < 5:
        # A degenerate probability vector: "none" = 1.0
        fake_probs = {NONE_CLASS_NAME: 1.0}
        picks = select_multi_distortions(
            fake_probs, threshold=threshold, max_count=max_count,
        )
        return {
            "text": t,
            "method": "empty",
            "multi_label": picks.to_dict(),
            "context": {
                "stress_score": stress_score,
                "anxiety_score": anxiety_score,
                "depression_score": depression_score,
            },
            "catalog": {},
        }

    # Try the ML path first
    if _model_loaded:
        try:
            X = _tfidf.transform([t])
            X_dense = X.toarray().astype(np.float32)
            probs = _clf.predict_proba(X_dense)[0]
            class_names = [
                _le.inverse_transform([i])[0] for i in range(len(probs))
            ]
            prob_dict = {
                name: float(p) for name, p in zip(class_names, probs)
            }
            method = "ml"
        except Exception as e:
            logger.error(
                f"ML multilabel analysis failed: {e}. Falling back to keywords."
            )
            prob_dict = _keyword_probs(t)
            method = "keyword_fallback"
    else:
        prob_dict = _keyword_probs(t)
        method = "keyword_fallback"

    # Apply the frozen CBT calibrator BEFORE thresholding. If no
    # calibration.json has been fitted yet, the service is an identity
    # pass-through so this is a no-op; once calibrated, the 0.20
    # threshold inside ``select_multi_distortions`` is interpreted
    # against genuinely-calibrated probabilities.
    raw_prob_dict = dict(prob_dict)
    calibrator = _cbt_calibrator()
    try:
        prob_dict = calibrator.calibrate_prob_dict(prob_dict)
    except Exception as e:
        logger.warning(
            f"CBT calibrator failed ({e}); using raw probabilities."
        )
        prob_dict = raw_prob_dict

    result = select_multi_distortions(
        prob_dict, threshold=threshold, max_count=max_count,
    )

    # Pull catalog entries for each pick so the UI can render reframes /
    # examples without a second round-trip.
    catalog_snippets = {}
    for pick in result.picks:
        entry = (_catalog or {}).get(pick.distortion_type, {})
        catalog_snippets[pick.distortion_type] = {
            "label": entry.get("label"),
            "description": entry.get("description"),
            "reframe_template": entry.get("reframe_template"),
            "examples": entry.get("examples", [])[:2],
        }

    return {
        "text": t,
        "method": method,
        "multi_label": result.to_dict(),
        "context": {
            "stress_score": stress_score,
            "anxiety_score": anxiety_score,
            "depression_score": depression_score,
        },
        "catalog": catalog_snippets,
        "calibration": {
            "applied": calibrator.is_fitted,
            "method": calibrator.method,
        },
    }


def _keyword_probs(text):
    """
    Build a quasi-probability vector from the keyword fallback.

    Normalises keyword counts to sum to 1 and allocates remaining mass
    to the "none" class so the multi-label selection logic sees a valid
    probability simplex. This is NOT a real softmax — it's the minimum
    viable input to keep the multilabel path working when the MLP fails
    to load.
    """
    text_lower = (text or "").lower()
    counts = {}
    for distortion, keywords in _KEYWORD_PATTERNS.items():
        c = sum(1 for kw in keywords if kw in text_lower)
        if c > 0:
            counts[distortion] = c

    total = sum(counts.values())
    probs = {name: 0.0 for name in _KEYWORD_PATTERNS.keys()}
    probs["none"] = 0.0
    if total == 0:
        probs["none"] = 1.0
        return probs

    # 80% of the mass goes to the detected distortions (weighted by
    # count), 20% reserved for "none" — the keyword heuristic is noisy
    # and we don't want to force a detection when a single throwaway
    # keyword matched.
    detected_mass = 0.80
    none_mass = 1.0 - detected_mass
    for name, c in counts.items():
        probs[name] = detected_mass * (c / total)
    probs["none"] = none_mass
    return probs
