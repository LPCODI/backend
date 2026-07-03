"""Database engine, session, and migration integration package."""

from app.db.base import (
    NAMING_CONVENTION,
    Base,
    BaseModel,
    BigIntPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from app.db.migrations import get_migration_database_url, get_migration_metadata
from app.db.session import (
    SessionLocal,
    check_database_connection,
    create_database_engine,
    create_session_factory,
    create_test_database_engine,
    create_test_session_factory,
    engine,
    get_db,
)
from app.db.testing import transactional_test_session

__all__ = [
    "NAMING_CONVENTION",
    "Base",
    "BaseModel",
    "BigIntPrimaryKeyMixin",
    "SessionLocal",
    "SoftDeleteMixin",
    "TimestampMixin",
    "check_database_connection",
    "create_database_engine",
    "create_session_factory",
    "create_test_database_engine",
    "create_test_session_factory",
    "engine",
    "get_db",
    "get_migration_database_url",
    "get_migration_metadata",
    "transactional_test_session",
]
