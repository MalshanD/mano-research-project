"""
Mood-Aware Dashboard Services — Free API Integrations

APIs integrated:
  1. Affirmations.dev — Unlimited, no key required
  2. ZenQuotes.io — 5 req/30s, no key required
  3. VADER Sentiment — Local Python lib, unlimited (for journal analysis)

All APIs are confirmed free (not trial periods) and production-ready.
"""

import httpx
import random
from typing import Optional, Dict, List
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class AffirmationService:
    """
    Fetches daily affirmations and motivational quotes from free APIs.
    Graceful fallback to local affirmations if APIs are unreachable.
    """

    AFFIRMATION_URL = "https://www.affirmations.dev"
    ZENQUOTES_URL = "https://zenquotes.io/api/random"

    # Local fallback affirmations (used when APIs are down)
    LOCAL_AFFIRMATIONS = [
        "You are worthy of love and respect.",
        "Every day is a new opportunity to grow and learn.",
        "Your feelings are valid and important.",
        "You are stronger than you think.",
        "It's okay to take things one step at a time.",
        "You deserve peace and happiness.",
        "Progress, not perfection, is what matters.",
        "You are doing the best you can, and that is enough.",
        "Your mental health matters. Taking care of yourself is not selfish.",
        "Small steps lead to big changes.",
        "You have the power to create positive change in your life.",
        "It's okay to ask for help when you need it.",
    ]

    LOCAL_QUOTES = [
        {"q": "The only way out is through.", "a": "Robert Frost"},
        {"q": "You don't have to control your thoughts. You just have to stop letting them control you.", "a": "Dan Millman"},
        {"q": "Mental health is not a destination, but a process.", "a": "Noam Shpancer"},
        {"q": "What mental health needs is more sunlight, more candor, and more unashamed conversation.", "a": "Glenn Close"},
        {"q": "You are not your illness. You have an individual story to tell.", "a": "Julian Seifter"},
        {"q": "Recovery is not one and done. It is a lifelong journey.", "a": "Unknown"},
    ]

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def get_affirmation(self) -> str:
        """Fetch a random affirmation from Affirmations.dev (unlimited, no key)."""
        try:
            client = await self._get_client()
            resp = await client.get(self.AFFIRMATION_URL)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("affirmation", random.choice(self.LOCAL_AFFIRMATIONS))
        except Exception:
            pass
        return random.choice(self.LOCAL_AFFIRMATIONS)

    async def get_motivational_quote(self) -> Dict:
        """Fetch a motivational quote from ZenQuotes (5 req/30s, no key)."""
        try:
            client = await self._get_client()
            resp = await client.get(self.ZENQUOTES_URL)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    return {"quote": data[0].get("q", ""), "author": data[0].get("a", "")}
        except Exception:
            pass
        fallback = random.choice(self.LOCAL_QUOTES)
        return {"quote": fallback["q"], "author": fallback["a"]}

    async def get_dashboard_content(self) -> Dict:
        """
        Get all mood-aware dashboard content in a single call.
        Used by the frontend Dashboard component on load.
        """
        affirmation = await self.get_affirmation()
        quote = await self.get_motivational_quote()

        return {
            "affirmation": affirmation,
            "motivational_quote": quote,
            "timestamp": datetime.now().isoformat(),
        }

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class JournalSentimentAnalyzer:
    """
    Analyzes journal entries using VADER sentiment (local, unlimited).
    Provides mood tracking data for the dashboard mood trajectory chart.
    """

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze_entry(self, text: str) -> Dict:
        """Analyze a single journal entry for sentiment."""
        scores = self.analyzer.polarity_scores(text)

        # Map compound score to a 1-10 mood scale for charting
        # VADER compound: -1.0 (very negative) to +1.0 (very positive)
        mood_score = round(((scores["compound"] + 1) / 2) * 9 + 1, 1)  # Maps to 1-10

        if scores["compound"] >= 0.05:
            mood_label = "positive"
        elif scores["compound"] <= -0.05:
            mood_label = "negative"
        else:
            mood_label = "neutral"

        return {
            "mood_score": mood_score,
            "mood_label": mood_label,
            "compound": round(scores["compound"], 3),
            "positive": round(scores["pos"], 3),
            "negative": round(scores["neg"], 3),
            "neutral": round(scores["neu"], 3),
        }

    def analyze_entries_batch(self, entries: List[Dict]) -> List[Dict]:
        """
        Analyze multiple journal entries for mood trajectory.
        Each entry should have: {text, created_at}
        """
        results = []
        for entry in entries:
            analysis = self.analyze_entry(entry.get("text", ""))
            analysis["date"] = entry.get("created_at", "")
            results.append(analysis)
        return results

    def get_mood_trend(self, entries: List[Dict]) -> Dict:
        """
        Calculate overall mood trend from journal entries.
        Returns: {trend: 'improving'|'declining'|'stable', avg_mood, change}
        """
        if not entries:
            return {"trend": "stable", "avg_mood": 5.0, "change": 0.0}

        analyzed = self.analyze_entries_batch(entries)
        mood_scores = [a["mood_score"] for a in analyzed]

        avg_mood = sum(mood_scores) / len(mood_scores)

        if len(mood_scores) >= 2:
            # Compare recent half vs. older half
            mid = len(mood_scores) // 2
            recent_avg = sum(mood_scores[mid:]) / len(mood_scores[mid:])
            older_avg = sum(mood_scores[:mid]) / len(mood_scores[:mid])
            change = recent_avg - older_avg

            if change > 0.5:
                trend = "improving"
            elif change < -0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            change = 0.0
            trend = "stable"

        return {
            "trend": trend,
            "avg_mood": round(avg_mood, 1),
            "change": round(change, 1),
            "data_points": len(mood_scores),
        }


# Global singletons
affirmation_service = AffirmationService()
journal_sentiment = JournalSentimentAnalyzer()
