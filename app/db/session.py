"""SQLAlchemy engine and session factory configuration."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_database_engine(
    settings: Settings | None = None,
    *,
    url: str | None = None,
) -> Engine:
    """Create the SQLAlchemy engine for a configured database URL."""

    app_settings = settings or get_settings()
    database_url = url or app_settings.database_url
    engine_options: dict[str, object] = {
        "echo": app_settings.database_echo,
        "pool_pre_ping": True,
    }
    if make_url(database_url).get_backend_name() != "sqlite":
        engine_options.update(
            pool_size=app_settings.database_pool_size,
            max_overflow=app_settings.database_max_overflow,
        )
    return create_engine(database_url, **engine_options)


def create_test_database_engine(settings: Settings | None = None) -> Engine:
    """Create an engine bound to the isolated test database URL."""

    app_settings = settings or get_settings()
    return create_database_engine(app_settings, url=app_settings.test_database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a SQLAlchemy 2.x session factory bound to the given engine."""

    return sessionmaker(
        bind=engine,
        class_=Session,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


engine = create_database_engine()
SessionLocal = create_session_factory(engine)


def create_test_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Create a session factory bound to the configured test database."""

    return create_session_factory(create_test_database_engine(settings))


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session for FastAPI dependencies."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection(database_engine: Engine | None = None) -> bool:
    """Run a minimal connectivity check against the configured database."""

    target_engine = database_engine or engine
    with target_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
