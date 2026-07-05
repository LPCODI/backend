import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings
from app.db import Base, get_db
from app.domain import DEFAULT_PRESENTATION_CONTEXT, ErrorCode, PresentationStatus
from app.main import create_app
from app.models import Presentation, RefreshToken, User
from app.services import PRESENTATION_INVALID_TIME_RANGE_MESSAGE


class PresentationCreateApiTest(unittest.TestCase):
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
        Base.metadata.create_all(
            self.engine,
            tables=[User.__table__, RefreshToken.__table__, Presentation.__table__],
        )
        self.settings = Settings(
            app_name="Presentation Create API Test",
            jwt_secret_key="presentation-create-api-test-secret",
            _env_file=None,
        )
        self.app = create_app(settings=self.settings)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(
            self.engine,
            tables=[Presentation.__table__, RefreshToken.__table__, User.__table__],
        )
        self.engine.dispose()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _signup_and_login(self, *, email: str = "presenter@example.com") -> dict[str, object]:
        signup = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": "correct horse battery staple",
                "name": "Presenter",
            },
        )
        self.assertEqual(signup.status_code, 201)
        login = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(login.status_code, 200)
        return login.json()["data"]

    def _authorization_header(self, token_data: dict[str, object]) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_data['access_token']}"}

    def test_create_presentation_persists_project_for_authenticated_user(self) -> None:
        tokens = self._signup_and_login()

        response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": " AI Speech Demo ",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["message"], "Created")
        self.assertEqual(payload["data"]["title"], "AI Speech Demo")
        self.assertEqual(payload["data"]["total_duration_seconds"], 600)
        self.assertEqual(payload["data"]["qa_duration_seconds"], 120)
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 480)
        self.assertEqual(payload["data"]["presentation_context"], DEFAULT_PRESENTATION_CONTEXT.value)
        self.assertEqual(payload["data"]["status"], PresentationStatus.DRAFT.value)
        self.assertEqual(payload["data"]["fixed_condition"]["presentation_target"], "담당 교수님")

        with self.session_factory() as session:
            presentation = session.execute(select(Presentation)).scalar_one()

        self.assertEqual(presentation.user_id, 1)
        self.assertEqual(presentation.title, "AI Speech Demo")
        self.assertEqual(presentation.presentation_duration_seconds, 480)
        self.assertEqual(presentation.presentation_context, DEFAULT_PRESENTATION_CONTEXT)

    def test_create_presentation_requires_authentication(self) -> None:
        response = self.client.post(
            "/api/v1/presentations",
            json={
                "title": "AI Speech Demo",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_create_presentation_rejects_fixed_condition_request_fields(self) -> None:
        tokens = self._signup_and_login()

        response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "AI Speech Demo",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
                "presentation_target": "custom target",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.VALIDATION_ERROR.value)

    def test_create_presentation_rejects_invalid_available_presentation_time(self) -> None:
        tokens = self._signup_and_login()

        response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "AI Speech Demo",
                "total_duration_seconds": 300,
                "qa_duration_seconds": 241,
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], ErrorCode.PRESENTATION_INVALID_TIME_RANGE.value)
        self.assertEqual(payload["error"]["message"], PRESENTATION_INVALID_TIME_RANGE_MESSAGE)
        self.assertEqual(payload["error"]["details"]["reason"], "presentation_duration_too_short")

    def test_list_presentations_returns_owned_non_deleted_projects_in_newest_order(self) -> None:
        owner_tokens = self._signup_and_login(email="owner@example.com")
        other_tokens = self._signup_and_login(email="other@example.com")

        archived_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Archived Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        active_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Active Project",
                "total_duration_seconds": 900,
                "qa_duration_seconds": 180,
            },
        )
        self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(other_tokens),
            json={
                "title": "Other User Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 60,
            },
        )

        archived_id = archived_response.json()["data"]["presentation_id"]
        with self.session_factory() as session:
            archived = session.get(Presentation, archived_id)
            self.assertIsNotNone(archived)
            archived.soft_delete()
            session.commit()

        response = self.client.get(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["presentation_id"], active_response.json()["data"]["presentation_id"])
        self.assertEqual(payload["data"][0]["title"], "Active Project")
        self.assertEqual(payload["data"][0]["presentation_duration_seconds"], 720)
        self.assertEqual(payload["data"][0]["fixed_condition"]["presentation_target"], "담당 교수님")

    def test_list_presentations_requires_authentication(self) -> None:
        response = self.client.get("/api/v1/presentations")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_get_presentation_returns_owned_project_detail(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Detail Project",
                "total_duration_seconds": 1200,
                "qa_duration_seconds": 300,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["presentation_id"], presentation_id)
        self.assertEqual(payload["data"]["title"], "Detail Project")
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 900)
        self.assertEqual(payload["data"]["presentation_context"], DEFAULT_PRESENTATION_CONTEXT.value)
        self.assertEqual(payload["data"]["fixed_condition"]["presentation_target"], "담당 교수님")

    def test_get_presentation_returns_not_found_for_other_user_project(self) -> None:
        owner_tokens = self._signup_and_login(email="detail-owner@example.com")
        other_tokens = self._signup_and_login(email="detail-other@example.com")
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Private Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(other_tokens),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_get_presentation_returns_not_found_for_soft_deleted_project(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Deleted Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]
        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)
            self.assertIsNotNone(presentation)
            presentation.soft_delete()
            session.commit()

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_get_presentation_requires_authentication(self) -> None:
        response = self.client.get("/api/v1/presentations/1")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)


if __name__ == "__main__":
    unittest.main()
