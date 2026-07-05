import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, verify_password
from app.db import Base, get_db
from app.domain import ErrorCode, UserRole, UserStatus
from app.main import create_app
from app.models import User
from app.services import USER_ALREADY_EXISTS_MESSAGE


class AuthSignupApiTest(unittest.TestCase):
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
        Base.metadata.create_all(self.engine, tables=[User.__table__])
        settings = Settings(
            app_name="Signup API Test",
            jwt_secret_key="signup-test-secret",
            _env_file=None,
        )
        self.app = create_app(settings=settings)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine, tables=[User.__table__])
        self.engine.dispose()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _read_user(self, email: str) -> User | None:
        with self.session_factory() as session:
            return session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def test_signup_creates_active_user_and_returns_public_profile(self) -> None:
        response = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": " New.Student@Example.COM ",
                "password": "correct horse battery staple",
                "name": " New Student ",
            },
        )
        payload = response.json()
        user = self._read_user("new.student@example.com")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["message"], "Created")
        self.assertNotIn("password", payload["data"])
        self.assertNotIn("password_hash", payload["data"])
        self.assertEqual(
            payload["data"],
            {
                "user_id": 1,
                "email": "new.student@example.com",
                "name": "New Student",
                "profile_image_url": None,
                "role": UserRole.USER.value,
                "status": UserStatus.ACTIVE.value,
                "created_at": payload["data"]["created_at"],
                "updated_at": payload["data"]["updated_at"],
            },
        )
        self.assertIsNotNone(user)
        assert user is not None
        self.assertTrue(verify_password("correct horse battery staple", user.password_hash))
        self.assertNotEqual(user.password_hash, "correct horse battery staple")

    def test_signup_rejects_duplicate_email_case_insensitively(self) -> None:
        first = self.client.post(
            "/api/v1/auth/signup",
            json={"email": "student@example.com", "password": "secret1234", "name": "Student"},
        )
        duplicate = self.client.post(
            "/api/v1/auth/signup",
            json={"email": "STUDENT@example.com", "password": "secret5678", "name": "Student 2"},
        )
        payload = duplicate.json()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.USER_ALREADY_EXISTS.value)
        self.assertEqual(payload["error"]["message"], USER_ALREADY_EXISTS_MESSAGE)

    def test_signup_uses_common_validation_failure_response(self) -> None:
        response = self.client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "short", "name": ""},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.VALIDATION_ERROR.value)
        error_locations = {tuple(error["loc"]) for error in payload["error"]["details"]["errors"]}
        self.assertGreaterEqual(
            error_locations,
            {
                ("body", "email"),
                ("body", "password"),
                ("body", "name"),
            },
        )


if __name__ == "__main__":
    unittest.main()
