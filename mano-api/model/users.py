"""User model — represents a registered guest user in the MANO platform."""
from sqlalchemy import Column, Integer, String, DateTime
from db.base import Base
from datetime import datetime


class User(Base):
    """A guest user account. Uses guest_name as the unique identifier.
    Password is hashed via bcrypt_sha256 (see util/security.py)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    guest_name = Column(String(255), unique=True, nullable=False)  # Acts as username
    password = Column(String(255), nullable=True)                  # bcrypt_sha256 hash
    created_at = Column(DateTime, default=datetime.now)
