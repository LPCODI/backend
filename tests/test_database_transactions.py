import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text

from app.core import Settings
from app.db import (
    check_database_connection,
    create_database_engine,
    transactional_test_session,
)


class DatabaseTransactionTest(unittest.TestCase):
    def test_transactional_test_session_rolls_back_committed_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_path = Path(tmp_dir) / "transaction-test.db"
            engine = create_database_engine(
                Settings(
                    database_url=f"sqlite+pysqlite:///{database_path}",
                    _env_file=None,
                )
            )

            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE TABLE transaction_probe "
                        "(id INTEGER PRIMARY KEY, name VARCHAR(50) NOT NULL)"
                    )
                )

            self.assertTrue(check_database_connection(engine))

            with transactional_test_session(engine) as session:
                session.execute(
                    text("INSERT INTO transaction_probe (name) VALUES (:name)"),
                    {"name": "rolled-back"},
                )
                session.commit()

                in_transaction_count = session.execute(
                    text("SELECT COUNT(*) FROM transaction_probe")
                ).scalar_one()
                self.assertEqual(in_transaction_count, 1)

            with engine.connect() as connection:
                persisted_count = connection.execute(
                    text("SELECT COUNT(*) FROM transaction_probe")
                ).scalar_one()

            self.assertEqual(persisted_count, 0)


if __name__ == "__main__":
    unittest.main()
