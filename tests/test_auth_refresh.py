import unittest
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, decode_access_token, hash_password, hash_refresh_token
from app.db import Base, get_db
from app.domain import ErrorCode, UserStatus
from app.main import create_app
from app.models import RefreshToken, User
from app.services import REFRESH_TOKEN_INVALID_MESSAGE


class AuthRefreshApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine, tables=[User.__table__, RefreshToken.__table__])
        self.settings = Settings(
            app_name="Refresh API Test",
            jwt_secret_key="refresh-test-secret",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
            _env_file=None,
        )
        self.app = create_app(settings=self.settings)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine, tables=[RefreshToken.__table__, User.__table__])
        self.engine.dispose()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _create_user_with_refresh_token(
        self,
        *,
        raw_token: str = "valid-refresh-token",
        status: UserStatus = UserStatus.ACTIVE,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="student@example.com",
                password_hash=hash_password("correct horse battery staple"),
                name="Student",
                status=status,
            )
            token = RefreshToken(
                refresh_token_id=1,
                user_id=1,
                token_hash=hash_refresh_token(raw_token),
                expires_at=expires_at or datetime.now(UTC) + timedelta(days=1),
                revoked_at=revoked_at,
            )
            session.add_all([user, token])
            session.commit()

    def test_refresh_rotates_refresh_token_and_issues_new_access_token(self) -> None:
        self._create_user_with_refresh_token()

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid-refresh-token"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["token_type"], "bearer")
        self.assertNotEqual(data["refresh_token"], "valid-refresh-token")
        self.assertEqual(data["user"]["email"], "student@example.com")

        access_payload = decode_access_token(data["access_token"], settings=self.settings)
        self.assertEqual(access_payload.user_id, 1)

        with self.session_factory() as session:
            tokens = session.scalars(
                select(RefreshToken).order_by(RefreshToken.refresh_token_id)
            ).all()

            self.assertEqual(len(tokens), 2)
            self.assertIsNotNone(tokens[0].revoked_at)
            self.assertEqual(tokens[1].token_hash, hash_refresh_token(data["refresh_token"]))
            self.assertIsNone(tokens[1].revoked_at)

    def test_refresh_rejects_unknown_token_without_creating_replacement(self) -> None:
        self._create_user_with_refresh_token()

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "unknown-refresh-token"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.TOKEN_INVALID.value)
        self.assertEqual(payload["error"]["message"], "Refresh token is invalid.")

        with self.session_factory() as session:
            token = session.execute(select(RefreshToken)).scalar_one()
            self.assertIsNone(token.revoked_at)

    def test_refresh_rejects_expired_refresh_token(self) -> None:
        self._create_user_with_refresh_token(
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid-refresh-token"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.TOKEN_EXPIRED.value)
        self.assertEqual(payload["error"]["message"], "Refresh token has expired.")

    def test_refresh_rejects_inactive_user_and_keeps_token_active(self) -> None:
        self._create_user_with_refresh_token(status=UserStatus.SUSPENDED)

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid-refresh-token"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.TOKEN_INVALID.value)
        self.assertEqual(payload["error"]["message"], REFRESH_TOKEN_INVALID_MESSAGE)

        with self.session_factory() as session:
            tokens = session.scalars(select(RefreshToken)).all()
            self.assertEqual(len(tokens), 1)
            self.assertIsNone(tokens[0].revoked_at)

    def test_refresh_uses_common_validation_failure_response(self) -> None:
        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "   "},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.VALIDATION_ERROR.value)


if __name__ == "__main__":
    unittest.main()
