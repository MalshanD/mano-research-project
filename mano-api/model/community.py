from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db.base import Base
from datetime import datetime

class Community(Base):
    __tablename__ = "community"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    community_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Optional: If you ever need to reference the user back.
    # user = relationship("User")