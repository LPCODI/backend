import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, decode_access_token, hash_password, hash_refresh_token
from app.db import Base, get_db
from app.domain import ErrorCode, UserStatus
from app.main import create_app
from app.models import RefreshToken, User
from app.services import INVALID_CREDENTIALS_MESSAGE


class AuthLoginApiTest(unittest.TestCase):
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
            app_name="Login API Test",
            jwt_secret_key="login-test-secret",
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

    def _create_user(
        self,
        *,
        email: str = "student@example.com",
        password: str = "correct horse battery staple",
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email=email,
                password_hash=hash_password(password),
                name="Student",
                status=status,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def test_login_issues_token_pair_and_updates_last_login(self) -> None:
        self._create_user(email="student@example.com")

        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": " Student@Example.COM ",
                "password": "correct horse battery staple",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["token_type"], "bearer")
        self.assertNotEqual(data["access_token"], data["refresh_token"])
        self.assertEqual(data["user"]["email"], "student@example.com")
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

        access_payload = decode_access_token(data["access_token"], settings=self.settings)
        self.assertEqual(access_payload.user_id, 1)

        with self.session_factory() as session:
            user = session.get(User, 1)
            token = session.execute(select(RefreshToken)).scalar_one()

            self.assertIsNotNone(user)
            assert user is not None
            self.assertIsNotNone(user.last_login_at)
            self.assertEqual(token.user_id, 1)
            self.assertEqual(token.token_hash, hash_refresh_token(data["refresh_token"]))
            self.assertNotEqual(token.token_hash, data["refresh_token"])
            self.assertIsNone(token.revoked_at)

    def test_login_rejects_wrong_password_with_common_failure_response(self) -> None:
        self._create_user()

        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.com", "password": "wrong-password"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.INVALID_CREDENTIALS.value)
        self.assertEqual(payload["error"]["message"], INVALID_CREDENTIALS_MESSAGE)

        with self.session_factory() as session:
            self.assertEqual(session.execute(select(RefreshToken)).all(), [])

    def test_login_rejects_inactive_user_as_invalid_credentials(self) -> None:
        self._create_user(status=UserStatus.SUSPENDED)

        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "student@example.com",
                "password": "correct horse battery staple",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.INVALID_CREDENTIALS.value)


if __name__ == "__main__":
    unittest.main()
