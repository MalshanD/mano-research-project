"""
Synchronous SQLAlchemy database engine.

Used by legacy ORM models (User, Question, etc.) that predate the async migration.
The async engine lives in core/database.py for newer models (Patient, SimulationResult).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import DATABASE_URL

# Connection pool to MySQL. pool_pre_ping sends a test query before reusing
# a connection to avoid "MySQL server has gone away" errors.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # Test connections before checkout
    pool_recycle=3600,    # Recycle stale connections every hour
    pool_size=10,         # Maintain 10 persistent connections
    max_overflow=20       # Allow up to 20 additional connections under load
)

# Session factory — each call to SessionLocal() creates one DB session.
# autoflush=False prevents implicit SQL before explicit commit.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """FastAPI dependency that provides a sync DB session.

    Usage in a route:
        @router.get("/users")
        def list_users(db: Session = Depends(get_db)):
            ...

    The session is guaranteed to close after the request finishes (via `finally`).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
