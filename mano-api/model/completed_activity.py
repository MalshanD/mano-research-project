from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from db.base import Base
from datetime import datetime

class CompletedActivity(Base):
    __tablename__ = "completed_activity"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_id = Column(String(50), index=True) # To quickly check if it exists so we can increment count
    activity_json = Column(JSON)
    count = Column(Integer, default=1)
    last_completed = Column(DateTime, default=datetime.now)
