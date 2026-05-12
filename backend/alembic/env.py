"""Alembic environment configuration for Nutrition AI backend.

Key points:
- Reads DATABASE_URL from the environment (or .env via pydantic-settings).
- Converts asyncpg:// → postgresql:// so Alembic can use a sync psycopg2 driver.
- Sets target_metadata = Base.metadata so autogenerate can diff the models.
- Runs migrations in offline mode (SQL scripts) or online mode (direct connection).
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make sure the app package is importable ──────────────────────────────────
# alembic is run from the `backend/` directory, so `app` is already on the path
# when prepend_sys_path = . is set in alembic.ini.  The explicit insert below
# acts as a safety net for editors and CI environments.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import all models so autogenerate can see them ───────────────────────────
# Importing `app.models` runs each model module and registers their Table
# objects on Base.metadata.
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  (side-effect: registers all tables)

# ── Alembic config object (wraps alembic.ini) ────────────────────────────────
config = context.config

# ── Logging ──────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Tell autogenerate which metadata to compare against ──────────────────────
target_metadata = Base.metadata


# ── Helper: derive a sync URL from the asyncpg URL ───────────────────────────
def _get_sync_url() -> str:
    """Return a psycopg2-compatible sync URL.

    Alembic uses a *synchronous* SQLAlchemy engine internally, so it cannot
    use asyncpg.  We convert:
        postgresql+asyncpg://user:pass@host/db
        → postgresql://user:pass@host/db   (uses psycopg2)

    The DATABASE_URL env var takes priority over alembic.ini so that the
    secret never has to be committed to the repository.
    """
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Export it before running alembic commands."
        )
    # Strip the async driver prefix so psycopg2 is used instead.
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


# ── Offline mode: emit SQL to stdout instead of connecting ───────────────────
def run_migrations_offline() -> None:
    """Generate a SQL script without an active DB connection.

    Useful for reviewing what will be applied before touching production.
    Run with:  alembic upgrade head --sql
    """
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas if you use Postgres schemas (e.g. public)
        include_schemas=False,
        # Compare server defaults so autogenerate catches DEFAULT value changes
        compare_server_defaults=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode: connect to the DB and apply migrations ──────────────────────
def run_migrations_online() -> None:
    """Apply migrations via a live database connection.

    Run with:  alembic upgrade head
    """
    sync_url = _get_sync_url()

    # Override whatever URL alembic.ini has with our derived sync URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No persistent pool needed for CLI migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_defaults=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
