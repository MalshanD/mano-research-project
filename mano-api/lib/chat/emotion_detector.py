"""
Emotion Detection Service using VADER Sentiment + GoEmotions Classification

Two layers of emotion analysis:
1. VADER Sentiment (local Python lib, unlimited, zero API cost)
   - Fast polarity scoring: positive, negative, neutral, compound
   - Used on EVERY message for real-time sentiment tracking

2. GoEmotions via HuggingFace Inference API (~1,000 req/day free)
   - Fine-grained 6-emotion classification: joy, sadness, anger, fear, surprise, disgust
   - Used selectively on emotional/complex messages to enrich Gemini context

Both layers are ADDITIVE — they do NOT replace the BERT intent classifier.
"""

import os
import httpx
from typing import Optional, Dict, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class EmotionDetector:
    """
    Dual-layer emotion analysis:
    - VADER for instant polarity (always available, local)
    - GoEmotions for fine-grained emotion labels (when HuggingFace API key is set)
    """

    # GoEmotions model on HuggingFace (6 basic emotions)
    HF_GOEMOTIONS_URL = (
        "https://api-inference.huggingface.co/models/"
        "SamLowe/roberta-base-go_emotions"
    )

    # Map GoEmotions' 28 labels → 6 core emotions for simpler downstream use
    EMOTION_GROUP_MAP = {
        "admiration": "joy", "amusement": "joy", "approval": "joy",
        "caring": "joy", "excitement": "joy", "gratitude": "joy",
        "joy": "joy", "love": "joy", "optimism": "joy", "pride": "joy",
        "relief": "joy",
        "anger": "anger", "annoyance": "anger", "disapproval": "anger",
        "disgust": "disgust",
        "embarrassment": "fear", "fear": "fear", "nervousness": "fear",
        "confusion": "surprise", "curiosity": "surprise",
        "realization": "surprise", "surprise": "surprise",
        "desire": "joy",
        "disappointment": "sadness", "grief": "sadness",
        "remorse": "sadness", "sadness": "sadness",
        "neutral": "neutral",
    }

    def __init__(self):
        # VADER is always available (pure Python, no API)
        self.vader = SentimentIntensityAnalyzer()
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "")
        self._hf_client: Optional[httpx.AsyncClient] = None

    # ── VADER (synchronous, local) ────────────────────────────────────────────

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Fast VADER polarity analysis.
        Returns: {neg, neu, pos, compound, label}
        compound ∈ [-1, 1]: >= 0.05 positive, <= -0.05 negative, else neutral
        """
        scores = self.vader.polarity_scores(text)

        if scores["compound"] >= 0.05:
            label = "positive"
        elif scores["compound"] <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return {
            "neg": round(scores["neg"], 3),
            "neu": round(scores["neu"], 3),
            "pos": round(scores["pos"], 3),
            "compound": round(scores["compound"], 3),
            "label": label,
        }

    # ── GoEmotions (async, HuggingFace API) ───────────────────────────────────

    async def detect_emotion(self, text: str) -> Optional[Dict]:
        """
        Fine-grained emotion detection via HuggingFace GoEmotions model.
        Returns: {emotion, confidence, raw_label} or None if unavailable.
        """
        if not self.hf_api_key:
            return None

        if self._hf_client is None or self._hf_client.is_closed:
            self._hf_client = httpx.AsyncClient(timeout=15.0)

        headers = {"Authorization": f"Bearer {self.hf_api_key}"}
        payload = {"inputs": text[:512]}  # Truncate to model max

        try:
            resp = await self._hf_client.post(
                self.HF_GOEMOTIONS_URL, json=payload, headers=headers
            )
            if resp.status_code == 200:
                results = resp.json()
                if results and isinstance(results, list):
                    # results is [[{label, score}, ...]] — take top prediction
                    top = results[0][0] if isinstance(results[0], list) else results[0]
                    raw_label = top["label"]
                    grouped = self.EMOTION_GROUP_MAP.get(raw_label, "neutral")
                    return {
                        "emotion": grouped,
                        "confidence": round(top["score"], 3),
                        "raw_label": raw_label,
                    }
            else:
                print(f"[EmotionDetector] HF API returned {resp.status_code}")
                return None

        except Exception as e:
            print(f"[EmotionDetector] GoEmotions error: {e}")
            return None

    # ── Combined analysis ─────────────────────────────────────────────────────

    async def full_analysis(self, text: str) -> Dict:
        """
        Run both VADER + GoEmotions and return combined result.
        VADER always runs; GoEmotions only when API key is set.
        """
        sentiment = self.analyze_sentiment(text)
        emotion = await self.detect_emotion(text)

        result = {"sentiment": sentiment}
        if emotion:
            result["emotion"] = emotion

        # Derive a simple emotional intensity flag
        compound = abs(sentiment["compound"])
        if compound >= 0.6:
            result["intensity"] = "high"
        elif compound >= 0.3:
            result["intensity"] = "moderate"
        else:
            result["intensity"] = "low"

        return result

    async def close(self):
        if self._hf_client and not self._hf_client.is_closed:
            await self._hf_client.aclose()


# Global singleton
emotion_detector = EmotionDetector()
