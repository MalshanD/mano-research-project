"""
Pydantic schemas for the Voice Journal service.

Design note
-----------
Voice journals are a common on-device intake channel, but the hardware target
(RTX 3050 Ti, 4 GB VRAM) rules out running Whisper-large locally on the same
box that serves the five frozen models. The pipeline is therefore split:

* **Audio → transcript** goes via a pluggable ``TranscriptionBackend``. In
  production we call the free Hugging Face Whisper inference API; if no key
  is configured, the router accepts pre-transcribed text so callers can
  sidestep the network round-trip entirely.
* **Transcript → analytics** is always local and CPU-bound: VADER for
  sentiment, an HF zero-shot / emotion classifier for affect distribution,
  lightweight keyword extraction for themes.

All heavy text inputs are sanitised before hitting an LLM prompt. Responses
carry the standard source-tag envelope (``live | cached | fallback | degraded``)
so the frontend can render trust/state badges without guessing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class VoiceJournalRequest(BaseModel):
    """Either an audio URL (will be transcribed) OR a pre-recorded transcript.

    Clients running on a resource-constrained device (e.g. the patient's phone)
    typically send ``audio_url``. Offline / test flows send ``transcript_text``
    directly to avoid the transcription hop.
    """

    audio_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        description=(
            "Publicly reachable URL to an audio file (wav/mp3/ogg/webm ≤ 25 MB). "
            "If omitted, ``transcript_text`` must be supplied."
        ),
    )
    transcript_text: Optional[str] = Field(
        default=None,
        max_length=8000,
        description="Pre-transcribed journal text (bypasses the transcription step).",
    )
    language_hint: Optional[str] = Field(
        default=None,
        max_length=8,
        description=(
            "Optional ISO-639-1 hint forwarded to the transcription backend "
            "(e.g. 'en', 'si', 'ta'). Improves accuracy for non-English audio."
        ),
    )
    include_emotion: bool = Field(
        default=True,
        description="Run the zero-shot emotion classifier. Disable to save quota.",
    )
    include_themes: bool = Field(
        default=True,
        description="Extract top keywords / themes from the transcript.",
    )
    max_themes: int = Field(default=5, ge=1, le=12)

    @field_validator("audio_url")
    @classmethod
    def _validate_audio_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("audio_url must be an http(s) URL")
        return v

    @model_validator(mode="after")
    def _require_one_input(self) -> "VoiceJournalRequest":
        if not self.audio_url and not (self.transcript_text and self.transcript_text.strip()):
            raise ValueError("Provide either audio_url or transcript_text.")
        return self


class EmotionScore(BaseModel):
    label: str = Field(..., description="Emotion label, e.g. 'joy', 'anger', 'fear'.")
    score: float = Field(..., ge=0.0, le=1.0)


class ThemeKeyword(BaseModel):
    term: str
    weight: float = Field(..., ge=0.0, le=1.0)


class VoiceJournalResponse(BaseModel):
    transcript: str = Field(
        ...,
        description="Final sanitised transcript (pass-through when caller supplied text).",
    )
    word_count: int

    # Sentiment — VADER compound score in [-1, 1] plus a categorical label.
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    sentiment_label: Literal["very_negative", "negative", "neutral", "positive", "very_positive"]

    # Emotion distribution (may be empty if classifier unavailable).
    emotion_distribution: List[EmotionScore] = Field(default_factory=list)
    dominant_emotion: Optional[str] = None

    # Theme extraction.
    themes: List[ThemeKeyword] = Field(default_factory=list)

    # Next-step suggestion — a short, gentle nudge derived from the analytics.
    suggested_action: str

    # Source envelope.
    transcription_source: Literal["provided", "live", "fallback", "degraded"] = Field(
        ..., description="How the transcript was obtained."
    )
    emotion_source: Literal["live", "cached", "fallback", "disabled"] = "disabled"
    analysed_at: datetime = Field(default_factory=datetime.utcnow)
    notes: List[str] = Field(default_factory=list)

    # Flags that the UI can use for amber / red banners.
    crisis_language_detected: bool = Field(
        default=False,
        description=(
            "True if the transcript matches the conservative crisis-keyword "
            "filter. Not a clinical determination — surfaces a UI banner only."
        ),
    )


class VoiceJournalListItem(BaseModel):
    """Compact row for dashboard history views."""
    analysed_at: datetime
    word_count: int
    sentiment_score: float
    sentiment_label: str
    dominant_emotion: Optional[str]
    themes: List[str] = Field(default_factory=list)


class EmotionSummary(BaseModel):
    """Per-emotion aggregate — used by history / trend endpoints."""
    label: str
    mean_score: float
    peak_score: float
    sample_count: int


class VoiceJournalTrendResponse(BaseModel):
    samples: int
    mean_sentiment: Optional[float] = None
    sentiment_trend: Literal["improving", "worsening", "stable", "insufficient_data"]
    top_emotions: List[EmotionSummary] = Field(default_factory=list)
    top_themes: List[ThemeKeyword] = Field(default_factory=list)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    notes: List[str] = Field(default_factory=list)
