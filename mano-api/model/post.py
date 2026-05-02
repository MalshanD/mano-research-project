import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Enum
from db.base import Base
from datetime import datetime

class PostType(enum.Enum):
    reflect = "reflect"
    milestone = "milestone"
    tip = "tip"
    discussion = "discussion"
    support = "support"

class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_type = Column(Enum(PostType), nullable=False)
    paragraph = Column(Text, nullable=False)
    community_id = Column(Integer, ForeignKey("community.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
