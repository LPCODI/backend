import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import UniqueConstraint, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db import Base
from app.domain.accounts import DEFAULT_USER_ROLE, DEFAULT_USER_STATUS, UserRole, UserStatus
from app.models import RefreshToken, User


class UserAuthModelTest(unittest.TestCase):
    def test_user_table_matches_auth_account_specification(self) -> None:
        columns = User.__table__.columns

        self.assertEqual(User.__tablename__, "users")
        self.assertIn("user_id", columns)
        self.assertNotIn("id", columns)
        self.assertTrue(columns["user_id"].primary_key)
        self.assertFalse(columns["email"].nullable)
        self.assertIn(
            "uq_users_email",
            {
                constraint.name
                for constraint in User.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )
        self.assertEqual(columns["email"].type.length, 255)
        self.assertEqual(columns["password_hash"].type.length, 255)
        self.assertEqual(columns["name"].type.length, 100)
        self.assertEqual(columns["role"].type.length, 30)
        self.assertEqual(columns["status"].type.length, 30)
        self.assertTrue(columns["profile_image_url"].nullable)
        self.assertTrue(columns["last_login_at"].nullable)
        self.assertTrue(columns["deleted_at"].index)

    def test_refresh_token_table_matches_token_specification(self) -> None:
        columns = RefreshToken.__table__.columns

        self.assertEqual(RefreshToken.__tablename__, "refresh_tokens")
        self.assertIn("refresh_token_id", columns)
        self.assertNotIn("id", columns)
        self.assertTrue(columns["refresh_token_id"].primary_key)
        self.assertFalse(columns["user_id"].nullable)
        self.assertTrue(columns["user_id"].index)
        self.assertFalse(columns["token_hash"].nullable)
        self.assertIn(
            "uq_refresh_tokens_token_hash",
            {
                constraint.name
                for constraint in RefreshToken.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )
        self.assertEqual(columns["token_hash"].type.length, 255)
        self.assertFalse(columns["expires_at"].nullable)
        self.assertTrue(columns["revoked_at"].nullable)
        self.assertFalse(columns["created_at"].nullable)

    def test_user_defaults_are_account_defaults_after_insert(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[User.__table__])

        with Session(engine) as session:
            user = User(
                user_id=1,
                email="professor-demo@example.com",
                password_hash="hash",
                name="Presenter",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        self.assertEqual(user.role, DEFAULT_USER_ROLE.value)
        self.assertEqual(user.status, DEFAULT_USER_STATUS.value)
        self.assertEqual(UserRole.USER, "USER")
        self.assertEqual(UserStatus.ACTIVE, "ACTIVE")

    def test_refresh_token_revocation_state(self) -> None:
        token = RefreshToken(
            refresh_token_id=1,
            user_id=1,
            token_hash="token-hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        self.assertFalse(token.is_revoked)
        token.revoke()

        self.assertTrue(token.is_revoked)
        self.assertIsNotNone(token.revoked_at)
        self.assertIs(token.revoked_at.tzinfo, UTC)

    def test_postgresql_ddl_contains_expected_keys_and_constraints(self) -> None:
        user_ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect())).upper()
        token_ddl = str(
            CreateTable(RefreshToken.__table__).compile(dialect=postgresql.dialect())
        ).upper()

        self.assertIn("USER_ID BIGINT GENERATED ALWAYS AS IDENTITY", user_ddl)
        self.assertIn("CONSTRAINT PK_USERS PRIMARY KEY (USER_ID)", user_ddl)
        self.assertIn("CONSTRAINT UQ_USERS_EMAIL UNIQUE (EMAIL)", user_ddl)
        self.assertIn("REFRESH_TOKEN_ID BIGINT GENERATED ALWAYS AS IDENTITY", token_ddl)
        self.assertIn("CONSTRAINT PK_REFRESH_TOKENS PRIMARY KEY (REFRESH_TOKEN_ID)", token_ddl)
        self.assertIn("CONSTRAINT UQ_REFRESH_TOKENS_TOKEN_HASH UNIQUE (TOKEN_HASH)", token_ddl)
        self.assertIn("FOREIGN KEY(USER_ID) REFERENCES USERS (USER_ID) ON DELETE CASCADE", token_ddl)

    def test_models_create_and_persist_in_sqlite_test_database(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[User.__table__, RefreshToken.__table__])

        inspector = inspect(engine)
        self.assertTrue(inspector.has_table("users"))
        self.assertTrue(inspector.has_table("refresh_tokens"))

        with Session(engine) as session:
            user = User(
                user_id=1,
                email="student@example.com",
                password_hash="hash",
                name="Student",
            )
            token = RefreshToken(
                refresh_token_id=1,
                user=user,
                token_hash="refresh-token-hash",
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add_all([user, token])
            session.commit()
            session.refresh(user)

            self.assertEqual(user.refresh_tokens[0].token_hash, "refresh-token-hash")
            self.assertIs(user.refresh_tokens[0].user, user)


if __name__ == "__main__":
    unittest.main()
