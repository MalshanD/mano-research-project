"""
Synchronous SQLAlchemy declarative base.

All legacy ORM models (User, Question, Response, ChatSession, etc.) inherit from
this Base. SQLAlchemy uses it to track which tables to CREATE/DROP.

NOTE: The async models (Patient, SimulationResult) use a SEPARATE Base defined
in core/database.py. Both bases coexist — main.py calls create_all on both.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
