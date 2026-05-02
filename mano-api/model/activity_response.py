from sqlalchemy import Column, Integer, DateTime, JSON, ForeignKey
from db.base import Base
from datetime import datetime

class ActivityResponse(Base):
    __tablename__ = "activity_response"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    result_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
