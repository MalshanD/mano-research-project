"""
Gemini Flash API Integration Service
Provides high-quality, context-aware therapeutic responses using Google Gemini Flash.
Free tier: 15 RPM, 1,500 req/day, 1M tokens/min — no credit card required.

This service is used as the SECONDARY response engine when:
  - BERT intent confidence is LOW (< 0.7)
  - The message is emotional/complex
  - The user's risk tier is elevated

The BERT intent classifier remains the PRIMARY first-pass triage (fast, local, free).
"""

import os
import json
import asyncio
import httpx
from typing import Optional, Dict, List
from datetime import datetime


# ── System prompts per persona ────────────────────────────────────────────────
PERSONA_SYSTEM_PROMPTS = {
    "friend": (
        "You are MANO, a warm and supportive AI companion for mental wellness. "
        "You speak like a caring, emotionally intelligent friend — not a clinician. "
        "Use casual but thoughtful language. Ask open-ended questions. Validate feelings "
        "before offering perspectives. Never diagnose. Never prescribe medication. "
        "If someone expresses crisis-level distress, gently suggest professional help "
        "and provide the crisis hotline number: 1393 (Sri Lanka) or 988 (US Suicide & Crisis Lifeline)."
    ),
    "counselor": (
        "You are MANO, an AI wellness counselor trained in supportive therapeutic techniques. "
        "Use empathetic, reflective listening. Mirror the user's language. Gently explore "
        "feelings and patterns. Use CBT-informed questions like 'What evidence supports that thought?' "
        "without using clinical jargon. Help users identify cognitive distortions in plain language. "
        "Never diagnose or prescribe. If crisis signals appear, provide the crisis hotline: "
        "1393 (Sri Lanka) or 988 (US)."
    ),
    "medical_officer": (
        "You are MANO, an AI health information assistant. Provide evidence-based mental health "
        "information in an accessible, professional tone. When discussing symptoms, frame them "
        "as 'experiences' not 'conditions'. Always recommend consulting a healthcare professional "
        "for specific medical concerns. Never diagnose, prescribe, or replace professional medical advice. "
        "Crisis hotline: 1393 (Sri Lanka) or 988 (US)."
    ),
}


class GeminiService:
    """
    Async wrapper around the Google Gemini Flash REST API.
    Uses the free-tier generativelanguage.googleapis.com endpoint (no GCP project needed).
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL = "gemini-2.0-flash"  # Free tier: 15 RPM, 1.5K req/day, 1M tok/min

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def generate_response(
        self,
        user_message: str,
        persona: str = "friend",
        conversation_history: Optional[List[Dict]] = None,
        user_context: Optional[Dict] = None,
        emotion_label: Optional[str] = None,
        detected_intent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a therapeutic response using Gemini Flash.

        Args:
            user_message: The user's current message
            persona: One of 'friend', 'counselor', 'medical_officer'
            conversation_history: Last N messages [{role, text}, ...]
            user_context: User profile data (risk scores, assessment results, etc.)
            emotion_label: Detected emotion from GoEmotions (e.g., 'sadness', 'anxiety')
            detected_intent: BERT-detected intent label

        Returns:
            Generated response text, or None if the API is unavailable / errors out.
        """
        if not self.is_available:
            return None

        # Build the system instruction
        system_prompt = PERSONA_SYSTEM_PROMPTS.get(persona, PERSONA_SYSTEM_PROMPTS["friend"])

        # Enrich system prompt with user context
        context_parts = []
        if user_context:
            if user_context.get("risk_tier"):
                context_parts.append(f"Current risk tier: {user_context['risk_tier']}")
            if user_context.get("stress_score") is not None:
                context_parts.append(
                    f"Latest assessment — Stress: {user_context['stress_score']}, "
                    f"Anxiety: {user_context.get('anxiety_score', 'N/A')}, "
                    f"Depression: {user_context.get('depression_score', 'N/A')}"
                )
            if user_context.get("streak_days"):
                context_parts.append(f"User has a {user_context['streak_days']}-day engagement streak")

        if emotion_label:
            context_parts.append(f"Detected emotion in this message: {emotion_label}")

        if detected_intent:
            context_parts.append(f"Detected intent: {detected_intent}")

        if context_parts:
            system_prompt += "\n\nUser context (use to personalize, do not repeat verbatim):\n- " + "\n- ".join(context_parts)

        # Build contents array (conversation history + current message)
        contents = []

        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context window
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["text"]}]
                })

        # Current user message
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        # API request payload
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.75,
                "topP": 0.9,
                "topK": 40,
                "maxOutputTokens": 350,
                "candidateCount": 1,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ],
        }

        url = f"{self.BASE_URL}/{self.MODEL}:generateContent?key={self.api_key}"

        try:
            client = await self._get_client()
            resp = await client.post(url, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            else:
                # Log but don't crash — fallback to BlenderBot/template
                print(f"[GeminiService] API returned {resp.status_code}: {resp.text[:200]}")
                return None

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f"[GeminiService] Network error: {e}")
            return None
        except Exception as e:
            print(f"[GeminiService] Unexpected error: {e}")
            return None

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global singleton
gemini_service = GeminiService()
