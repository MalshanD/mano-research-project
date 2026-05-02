from pydantic import BaseModel
from typing import Optional, List

class RecommendationRequest(BaseModel):
    """
    Request model for recommendations.
    Accepts 20 answers to the assessment questions.
    Each answer is expected to be on a 1-5 scale.
    """
    # List of exactly 20 answers (1-5 scale)
    # 0-4: Body Score
    # 5-9: Behavior Score
    # 10-14: Emotional Score
    # 15-19: Social Score
    answers: Optional[List[int]] = None

    # Preferences
    num_recommendations: Optional[int] = 3
    difficulty_preference: Optional[str] = 'easy'
    max_duration_minutes: Optional[int] = None
    exclude_categories: Optional[List[str]] = None

class CompleteActivityRequest(BaseModel):
    activity_id: str


class ActivityFeedbackRequest(BaseModel):
    activity_id: str
    effectiveness_rating: int  # 1-5 stars
    mood_before: Optional[int] = None  # 1-5
    mood_after: Optional[int] = None   # 1-5
    feedback_note: Optional[str] = None
    would_recommend: Optional[int] = None  # 1=no, 2=maybe, 3=yes
