import unittest

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core import Settings
from app.db import (
    SessionLocal,
    check_database_connection,
    create_database_engine,
    create_session_factory,
    create_test_database_engine,
    create_test_session_factory,
    get_db,
)


class DatabaseSessionTest(unittest.TestCase):
    def test_default_database_url_uses_postgresql_psycopg_driver(self) -> None:
        engine = create_database_engine(Settings(_env_file=None))

        self.assertIsInstance(engine, Engine)
        self.assertEqual(engine.url.drivername, "postgresql+psycopg")
        self.assertEqual(engine.url.database, "ai_speech")
        self.assertTrue(engine.pool._pre_ping)

    def test_session_factory_is_bound_to_engine_with_expected_options(self) -> None:
        engine = create_database_engine(
            Settings(database_url="sqlite+pysqlite:///:memory:", _env_file=None)
        )
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            self.assertIsInstance(session, Session)
            self.assertEqual(session.execute(text("SELECT 1")).scalar_one(), 1)
            self.assertFalse(session.autoflush)
            self.assertFalse(session.expire_on_commit)

    def test_test_database_engine_uses_isolated_configured_url(self) -> None:
        settings = Settings(
            database_url="sqlite+pysqlite:///runtime.db",
            test_database_url="sqlite+pysqlite:///:memory:",
            _env_file=None,
        )

        engine = create_test_database_engine(settings)
        session_factory = create_test_session_factory(settings)

        self.assertEqual(engine.url.drivername, "sqlite+pysqlite")
        self.assertEqual(str(engine.url), "sqlite+pysqlite:///:memory:")
        with session_factory() as session:
            self.assertEqual(session.execute(text("SELECT 1")).scalar_one(), 1)

    def test_get_db_yields_request_scoped_session(self) -> None:
        dependency = get_db()
        session = next(dependency)

        try:
            self.assertIsInstance(session, Session)
            self.assertIs(session.bind, SessionLocal.kw["bind"])
        finally:
            with self.assertRaises(StopIteration):
                next(dependency)

    def test_check_database_connection_runs_select_one(self) -> None:
        engine = create_database_engine(
            Settings(database_url="sqlite+pysqlite:///:memory:", _env_file=None)
        )

        self.assertTrue(check_database_connection(engine))


if __name__ == "__main__":
    unittest.main()
