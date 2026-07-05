import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core import Settings
from app.db import Base, get_db
from app.domain import ErrorCode
from app.main import create_app
from app.models import RefreshToken, User


class AuthAuthorizationIntegrationTest(unittest.TestCase):
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
            app_name="Auth Authorization Integration Test",
            jwt_secret_key="auth-authorization-integration-test-secret",
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

    def _signup(self, *, email: str, name: str) -> dict[str, object]:
        response = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": "correct horse battery staple",
                "name": name,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]

    def _login(self, *, email: str) -> dict[str, object]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def _authorization_header(self, token_data: dict[str, object]) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_data['access_token']}"}

    def test_signup_login_and_protected_user_api_use_authenticated_identity(self) -> None:
        first_user = self._signup(email="first@example.com", name="First Student")
        second_user = self._signup(email="second@example.com", name="Second Student")
        first_tokens = self._login(email="first@example.com")
        second_tokens = self._login(email="second@example.com")

        first_me = self.client.get(
            "/api/v1/users/me",
            headers=self._authorization_header(first_tokens),
        )
        second_me = self.client.get(
            "/api/v1/users/me",
            headers=self._authorization_header(second_tokens),
        )

        self.assertEqual(first_me.status_code, 200)
        self.assertEqual(second_me.status_code, 200)
        self.assertEqual(first_me.json()["data"]["user_id"], first_user["user_id"])
        self.assertEqual(second_me.json()["data"]["user_id"], second_user["user_id"])
        self.assertNotEqual(first_me.json()["data"]["user_id"], second_me.json()["data"]["user_id"])
        self.assertEqual(first_me.json()["data"]["email"], "first@example.com")
        self.assertEqual(second_me.json()["data"]["email"], "second@example.com")

        update_response = self.client.patch(
            "/api/v1/users/me",
            headers=self._authorization_header(first_tokens),
            json={"name": "First Presenter"},
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["user_id"], first_user["user_id"])
        self.assertEqual(update_response.json()["data"]["name"], "First Presenter")

        with self.session_factory() as session:
            users = session.scalars(select(User).order_by(User.user_id)).all()

            self.assertEqual(len(users), 2)
            self.assertEqual(users[0].name, "First Presenter")
            self.assertEqual(users[1].name, "Second Student")

    def test_protected_api_requires_valid_bearer_token(self) -> None:
        missing_token = self.client.get("/api/v1/users/me")
        malformed_token = self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )

        self.assertEqual(missing_token.status_code, 401)
        self.assertEqual(
            missing_token.json()["error"]["code"],
            ErrorCode.AUTHENTICATION_REQUIRED.value,
        )
        self.assertEqual(malformed_token.status_code, 401)
        self.assertEqual(
            malformed_token.json()["error"]["code"],
            ErrorCode.TOKEN_INVALID.value,
        )

    def test_logout_revokes_only_current_users_refresh_token_and_blocks_reuse(self) -> None:
        self._signup(email="first@example.com", name="First Student")
        self._signup(email="second@example.com", name="Second Student")
        first_tokens = self._login(email="first@example.com")
        second_tokens = self._login(email="second@example.com")

        logout_response = self.client.post(
            "/api/v1/auth/logout",
            headers=self._authorization_header(first_tokens),
            json={"refresh_token": first_tokens["refresh_token"]},
        )
        first_refresh_response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_tokens["refresh_token"]},
        )
        second_refresh_response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": second_tokens["refresh_token"]},
        )

        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.json()["data"]["revoked"])
        self.assertEqual(first_refresh_response.status_code, 401)
        self.assertEqual(
            first_refresh_response.json()["error"]["code"],
            ErrorCode.TOKEN_INVALID.value,
        )
        self.assertEqual(second_refresh_response.status_code, 200)
        self.assertTrue(second_refresh_response.json()["success"])

        with self.session_factory() as session:
            tokens = session.scalars(select(RefreshToken).order_by(RefreshToken.refresh_token_id)).all()

            self.assertEqual(len(tokens), 3)
            self.assertIsNotNone(tokens[0].revoked_at)
            self.assertIsNotNone(tokens[1].revoked_at)
            self.assertIsNone(tokens[2].revoked_at)


if __name__ == "__main__":
    unittest.main()
