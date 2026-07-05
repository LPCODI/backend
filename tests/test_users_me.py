import unittest
from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, create_access_token
from app.db import Base, get_db
from app.domain import ErrorCode, UserRole, UserStatus
from app.main import create_app
from app.models import User


class UsersMeApiTest(unittest.TestCase):
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
        self.settings = Settings(
            app_name="Users Me API Test",
            jwt_secret_key="users-me-test-secret",
            _env_file=None,
        )
        self.app = create_app(settings=self.settings)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine, tables=[User.__table__])
        self.engine.dispose()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _create_user(self) -> User:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="student@example.com",
                password_hash="hash",
                name="Student Presenter",
                profile_image_url="https://cdn.example.com/profiles/student.png",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def _access_token(self, user_id: int = 1) -> str:
        return create_access_token(
            user_id=user_id,
            settings=self.settings,
            issued_at=datetime.now(UTC),
        )

    def test_get_me_returns_authenticated_user_public_profile(self) -> None:
        user = self._create_user()
        response = self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self._access_token(user.user_id)}"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertNotIn("password", payload["data"])
        self.assertNotIn("password_hash", payload["data"])
        self.assertEqual(
            payload["data"],
            {
                "user_id": 1,
                "email": "student@example.com",
                "name": "Student Presenter",
                "profile_image_url": "https://cdn.example.com/profiles/student.png",
                "role": UserRole.USER.value,
                "status": UserStatus.ACTIVE.value,
                "created_at": payload["data"]["created_at"],
                "updated_at": payload["data"]["updated_at"],
            },
        )

    def test_get_me_requires_access_token(self) -> None:
        response = self.client.get("/api/v1/users/me")
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_patch_me_updates_authenticated_user_profile(self) -> None:
        user = self._create_user()
        response = self.client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self._access_token(user.user_id)}"},
            json={
                "name": " Updated Presenter ",
                "profile_image_url": " https://cdn.example.com/profiles/updated.png ",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["name"], "Updated Presenter")
        self.assertEqual(
            payload["data"]["profile_image_url"],
            "https://cdn.example.com/profiles/updated.png",
        )
        self.assertNotIn("password_hash", payload["data"])

        with self.session_factory() as session:
            updated_user = session.get(User, user.user_id)

            self.assertIsNotNone(updated_user)
            assert updated_user is not None
            self.assertEqual(updated_user.name, "Updated Presenter")
            self.assertEqual(
                updated_user.profile_image_url,
                "https://cdn.example.com/profiles/updated.png",
            )

    def test_patch_me_can_clear_profile_image_url(self) -> None:
        user = self._create_user()
        response = self.client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self._access_token(user.user_id)}"},
            json={"profile_image_url": None},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertIsNone(payload["data"]["profile_image_url"])

        with self.session_factory() as session:
            updated_user = session.get(User, user.user_id)

            self.assertIsNotNone(updated_user)
            assert updated_user is not None
            self.assertIsNone(updated_user.profile_image_url)

    def test_patch_me_requires_access_token(self) -> None:
        response = self.client.patch("/api/v1/users/me", json={"name": "Updated Presenter"})
        payload = response.json()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_patch_me_uses_common_validation_failure_response(self) -> None:
        self._create_user()
        response = self.client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={"email": "changed@example.com"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.VALIDATION_ERROR.value)


if __name__ == "__main__":
    unittest.main()
