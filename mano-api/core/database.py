# """
# MANO Database Configuration.
# Async SQLAlchemy engine with SQLite for development.

# WHY ASYNC?
# Our FastAPI endpoints are async. If we use a regular (sync) database connection,
# every DB query blocks the event loop and prevents other requests from being processed.
# Async DB I/O lets the server handle multiple requests concurrently — e.g., one request
# is waiting for DB while another runs GPU inference.

# TO SWITCH TO POSTGRESQL IN PRODUCTION:
# Change DATABASE_URL to:
#     "postgresql+asyncpg://user:pass@host:5432/mano"
# And install: pip install asyncpg
# """
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
# from sqlalchemy.orm import DeclarativeBase
# from pathlib import Path

# # SQLite file lives next to the app directory
# _db_path = Path(__file__).resolve().parent.parent / "mano.db"
# DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

# # The engine is the connection pool — it manages a pool of database connections.
# engine = create_async_engine(
#     DATABASE_URL,
#     echo=False,  # Set True to see raw SQL in logs (noisy but useful for debugging)
# )

# # The session factory creates new sessions (one per request).
# async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# class Base(DeclarativeBase):
#     """
#     All ORM models inherit from this.
#     SQLAlchemy uses it to track which tables need to be created.
#     """
#     pass


# async def create_tables():
#     """
#     Creates all tables that don't exist yet.
#     Called once during app startup (in main.py lifespan).
#     """
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


# async def get_db():
#     """
#     FastAPI dependency that provides a database session.

#     Usage in a route:
#         @router.get("/patients")
#         async def list_patients(db: AsyncSession = Depends(get_db)):
#             ...

#     The session is automatically closed after the request finishes.
#     """
#     async with async_session() as session:
#         yield session

"""
Async MySQL Database Configuration (core/database.py).

Used by newer ORM models (Patient, SimulationResult) that need async I/O.
Async DB queries let FastAPI handle concurrent requests efficiently — one request
can wait for DB while another runs GPU inference on a different event loop tick.

To switch databases, change the URL scheme:
  - MySQL:  mysql+aiomysql://user:pass@host:port/db
  - Postgres: postgresql+asyncpg://user:pass@host:5432/db
  - SQLite:   sqlite+aiosqlite:///path/to/db
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Connection string for the async MySQL driver (aiomysql).
# URL-encode special characters in passwords (e.g., @ → %40).
DATABASE_URL = "mysql+aiomysql://devuser:DevPass2024@107.174.201.30:3307/myapp_dev"

# Async connection pool with MySQL-specific resilience settings.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # Set True to log every SQL query (noisy but useful for debugging)
    pool_pre_ping=True,  # Auto-reconnect stale connections before use
    pool_recycle=3600,   # Recycle connections every hour to prevent timeout
)

# Factory for creating per-request async sessions.
# expire_on_commit=False keeps ORM objects usable after commit without re-querying.
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all async ORM models (Patient, SimulationResult).
    SQLAlchemy uses subclasses to auto-discover which tables to create."""
    pass


async def create_tables():
    """Create all tables that don't yet exist in the database.
    Called once during app startup via the lifespan manager in main.py."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency that provides an async DB session.

    Usage in an async route:
        @router.get("/patients")
        async def list_patients(db: AsyncSession = Depends(get_db)):
            ...

    The session auto-closes when the request finishes.
    """
    async with async_session() as session:
        yield session
