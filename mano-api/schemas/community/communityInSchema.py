from pydantic import BaseModel
from typing import Optional


class CreatePostRequest(BaseModel):
    post_type: str
    paragraph: str


class MoodCheckInRequest(BaseModel):
    mood: str  # great, good, okay, low, bad


class ReactionRequest(BaseModel):
    reaction_type: str  # heart, hug, celebrate, insightful, strength, laugh


class JournalEntryRequest(BaseModel):
    entry_text: str
    entry_date: Optional[str] = None  # ISO date string (YYYY-MM-DD), defaults to today


class JournalAnalyzeRequest(BaseModel):
    text: str


class JournalFeedbackRequest(BaseModel):
    found_helpful: bool
