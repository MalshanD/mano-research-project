import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, UniqueConstraint
from db.base import Base
from datetime import datetime


class ReactionType(enum.Enum):
    heart = "heart"          # ❤️  Classic love
    hug = "hug"              # 🤗  Supportive embrace
    celebrate = "celebrate"  # 🎉  Celebrating wins
    insightful = "insightful"  # 💡  Learned something
    strength = "strength"    # 💪  Shows strength
    laugh = "laugh"          # 😂  Funny / lightened mood


# Emoji + label mapping for frontend/API responses
REACTION_CATALOG = {
    ReactionType.heart:      {"emoji": "❤️",  "label": "Love"},
    ReactionType.hug:        {"emoji": "🤗", "label": "Hug"},
    ReactionType.celebrate:  {"emoji": "🎉", "label": "Celebrate"},
    ReactionType.insightful: {"emoji": "💡", "label": "Insightful"},
    ReactionType.strength:   {"emoji": "💪", "label": "Strength"},
    ReactionType.laugh:      {"emoji": "😂", "label": "Haha"},
}


class PostReaction(Base):
    __tablename__ = "post_reaction"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("post.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction_type = Column(Enum(ReactionType), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Each user can only give one reaction of each type per post
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", "reaction_type", name="uq_user_post_reaction"),
    )
