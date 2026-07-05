import unittest
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, create_access_token, hash_password, hash_refresh_token
from app.db import Base, get_db
from app.domain import ErrorCode, UserStatus
from app.main import create_app
from app.models import RefreshToken, User


class AuthLogoutApiTest(unittest.TestCase):
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
            app_name="Logout API Test",
            jwt_secret_key="logout-test-secret",
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

    def _access_token(self, *, user_id: int = 1) -> str:
        return create_access_token(
            user_id=user_id,
            settings=self.settings,
            issued_at=datetime.now(UTC),
        )

    def _create_user_with_refresh_token(
        self,
        *,
        user_id: int = 1,
        email: str = "student@example.com",
        raw_token: str = "valid-refresh-token",
        status: UserStatus = UserStatus.ACTIVE,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        with self.session_factory() as session:
            user = User(
                user_id=user_id,
                email=email,
                password_hash=hash_password("correct horse battery staple"),
                name="Student",
                status=status,
            )
            token = RefreshToken(
                refresh_token_id=user_id,
                user_id=user_id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=expires_at or datetime.now(UTC) + timedelta(days=1),
                revoked_at=revoked_at,
            )
            session.add_all([user, token])
            session.commit()

    def _post_logout(
        self,
        *,
        access_token: str | None,
        refresh_token: str = "valid-refresh-token",
    ):
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        return self.client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )

    def test_logout_revokes_current_users_refresh_token(self) -> None:
        self._create_user_with_refresh_token()

        response = self._post_logout(access_token=self._access_token())
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"], {"revoked": True})

        with self.session_factory() as session:
            token = session.execute(select(RefreshToken)).scalar_one()
            self.assertIsNotNone(token.revoked_at)

    def test_logout_requires_access_token(self) -> None:
        self._create_user_with_refresh_token()

        response = self._post_logout(access_token=None)
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_logout_rejects_refresh_token_owned_by_another_user(self) -> None:
        self._create_user_with_refresh_token(user_id=1, raw_token="user-one-token")
        self._create_user_with_refresh_token(
            user_id=2,
            email="other@example.com",
            raw_token="other-user-token",
        )

        response = self._post_logout(
            access_token=self._access_token(user_id=1),
            refresh_token="other-user-token",
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.TOKEN_INVALID.value)

        with self.session_factory() as session:
            other_token = session.scalar(
                select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token("other-user-token"))
            )
            self.assertIsNotNone(other_token)
            self.assertIsNone(other_token.revoked_at)

    def test_logout_rejects_unknown_and_expired_refresh_tokens(self) -> None:
        self._create_user_with_refresh_token(
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        unknown = self._post_logout(
            access_token=self._access_token(),
            refresh_token="unknown-refresh-token",
        )
        expired = self._post_logout(access_token=self._access_token())

        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.json()["error"]["code"], ErrorCode.TOKEN_INVALID.value)
        self.assertEqual(expired.status_code, 401)
        self.assertEqual(expired.json()["error"]["code"], ErrorCode.TOKEN_EXPIRED.value)

    def test_logout_uses_common_validation_failure_response(self) -> None:
        self._create_user_with_refresh_token()

        response = self._post_logout(access_token=self._access_token(), refresh_token="   ")
        payload = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.VALIDATION_ERROR.value)


if __name__ == "__main__":
    unittest.main()
