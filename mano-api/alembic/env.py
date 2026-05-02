"""
Alembic environment — MANO backend.

Design points
-------------
* Database URL is resolved at runtime from ``core.config.settings`` rather than
  alembic.ini. Keeps production credentials out of the repo.
* ``target_metadata`` is sourced from ``db.base.Base.metadata`` after importing
  every model module (via ``model/__init__.py``). Without the import side-
  effect, autogenerate would miss half the tables.
* We run migrations against the synchronous engine defined in ``db.database``
  because Alembic's autogeneration has better support for the sync path —
  the async engine is used only for request-time I/O.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

# ── Make the project root importable ────────────────────────────────────────
# env.py is invoked from alembic/; our application modules live one level up.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from alembic import context  # noqa: E402  (sys.path must be set first)

# Side-effect: registers every ORM model on ``Base.metadata``.
import model  # noqa: F401,E402
from core.config import settings  # noqa: E402
from db.base import Base  # noqa: E402


# ── Alembic config object ──────────────────────────────────────────────────
config = context.config

# Propagate the runtime DATABASE_URL into Alembic's config slot. Alembic's
# own ``sqlalchemy.url`` setting in alembic.ini is left blank on purpose.
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without an actual DB connection — emits SQL to stdout."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
