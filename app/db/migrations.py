"""Alembic migration helpers."""

from sqlalchemy import MetaData

from app.core.config import Settings, get_settings
from app.db.base import Base


def get_migration_database_url(settings: Settings | None = None) -> str:
    """Return the runtime database URL used by Alembic."""

    app_settings = settings or get_settings()
    return app_settings.database_url


def get_migration_metadata() -> MetaData:
    """Return SQLAlchemy metadata for Alembic autogeneration."""

    import app.models  # noqa: F401

    return Base.metadata
