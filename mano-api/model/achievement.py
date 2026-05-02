import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from db.base import Base
from datetime import datetime


class BadgeType(enum.Enum):
    # Streak badges
    streak_3 = "streak_3"
    streak_7 = "streak_7"
    streak_14 = "streak_14"
    streak_30 = "streak_30"

    # Activity completion badges
    first_step = "first_step"
    active_5 = "active_5"
    active_10 = "active_10"
    active_25 = "active_25"
    active_50 = "active_50"

    # Community engagement badges
    first_post = "first_post"
    community_voice = "community_voice"       # 5 posts
    social_butterfly = "social_butterfly"     # 10 posts

    # Mood tracking badges
    mood_starter = "mood_starter"             # First mood check-in
    mood_warrior = "mood_warrior"             # 7 consecutive mood check-ins
    mood_master = "mood_master"               # 30 mood check-ins total

    # Special badges
    wellness_explorer = "wellness_explorer"   # Complete activities from 3+ categories
    consistency_king = "consistency_king"     # 7-day streak + mood + post in same week


# Badge metadata (display info)
BADGE_CATALOG = {
    BadgeType.streak_3: {
        "name": "Warming Up",
        "description": "Maintained a 3-day activity streak",
        "icon": "fire",
        "tier": "bronze",
    },
    BadgeType.streak_7: {
        "name": "Week Warrior",
        "description": "Maintained a 7-day activity streak",
        "icon": "fire",
        "tier": "silver",
    },
    BadgeType.streak_14: {
        "name": "Fortnight Fighter",
        "description": "Maintained a 14-day activity streak",
        "icon": "fire",
        "tier": "gold",
    },
    BadgeType.streak_30: {
        "name": "Monthly Master",
        "description": "Maintained a 30-day activity streak",
        "icon": "fire",
        "tier": "platinum",
    },
    BadgeType.first_step: {
        "name": "First Step",
        "description": "Completed your first wellness activity",
        "icon": "sparkles",
        "tier": "bronze",
    },
    BadgeType.active_5: {
        "name": "Getting Active",
        "description": "Completed 5 wellness activities",
        "icon": "check-circle",
        "tier": "bronze",
    },
    BadgeType.active_10: {
        "name": "Dedicated",
        "description": "Completed 10 wellness activities",
        "icon": "check-circle",
        "tier": "silver",
    },
    BadgeType.active_25: {
        "name": "Wellness Champion",
        "description": "Completed 25 wellness activities",
        "icon": "trophy",
        "tier": "gold",
    },
    BadgeType.active_50: {
        "name": "Wellness Legend",
        "description": "Completed 50 wellness activities",
        "icon": "trophy",
        "tier": "platinum",
    },
    BadgeType.first_post: {
        "name": "Hello World",
        "description": "Created your first community post",
        "icon": "chat",
        "tier": "bronze",
    },
    BadgeType.community_voice: {
        "name": "Community Voice",
        "description": "Created 5 community posts",
        "icon": "chat",
        "tier": "silver",
    },
    BadgeType.social_butterfly: {
        "name": "Social Butterfly",
        "description": "Created 10 community posts",
        "icon": "users",
        "tier": "gold",
    },
    BadgeType.mood_starter: {
        "name": "Mood Tracker",
        "description": "Logged your first mood check-in",
        "icon": "heart",
        "tier": "bronze",
    },
    BadgeType.mood_warrior: {
        "name": "Mood Warrior",
        "description": "Logged mood for 7 consecutive days",
        "icon": "heart",
        "tier": "silver",
    },
    BadgeType.mood_master: {
        "name": "Mood Master",
        "description": "Logged 30 mood check-ins total",
        "icon": "heart",
        "tier": "gold",
    },
    BadgeType.wellness_explorer: {
        "name": "Wellness Explorer",
        "description": "Completed activities from 3+ categories",
        "icon": "compass",
        "tier": "silver",
    },
    BadgeType.consistency_king: {
        "name": "Consistency King",
        "description": "7-day streak with mood check-ins and posts in the same week",
        "icon": "crown",
        "tier": "gold",
    },
}


class Achievement(Base):
    """Tracks earned badges per user. One row per badge per user."""
    __tablename__ = "achievement"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_type = Column(Enum(BadgeType), nullable=False)
    earned_at = Column(DateTime, default=datetime.now)
