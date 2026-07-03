"""Database testing helpers."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session


@contextmanager
def transactional_test_session(engine: Engine) -> Iterator[Session]:
    """Yield a session whose writes are rolled back when the context exits."""

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
