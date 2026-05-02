from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from db.base import Base
from datetime import datetime
import enum


class SenderEnum(str, enum.Enum):
    USER = "USER"
    MODEL = "MODEL"


class RoleTypeEnum(str, enum.Enum):
    FRIEND = "FRIEND"
    DOCTOR = "MEDICAL_OFFICER"
    CONSULTOR = "COUNSELOR"


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_session.id"), nullable=False)
    sender = Column(SAEnum(SenderEnum), nullable=False)
    role_type = Column(SAEnum(RoleTypeEnum), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("ChatSession", back_populates="messages")
