import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import ApiError
from app.core import Settings
from app.db import Base, get_db
from app.domain import DEFAULT_PRESENTATION_CONTEXT, ErrorCode, PresentationStatus
from app.main import create_app
from app.models import Presentation, RefreshToken, User
from app.services import (
    PRESENTATION_DUPLICATE_TITLE_SUFFIX,
    PRESENTATION_INVALID_STATUS_TRANSITION_MESSAGE,
    PRESENTATION_INVALID_TIME_RANGE_MESSAGE,
    get_allowed_presentation_status_transitions,
    get_owned_presentation_project,
    transition_presentation_project_status,
    validate_presentation_status_transition,
)


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

    def test_presentation_project_openapi_exposes_completed_crud_routes(self) -> None:
        response = self.client.get("/openapi.json")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        presentation_paths = {
            "/api/v1/presentations": {"get", "post"},
            "/api/v1/presentations/{presentationId}": {"get", "patch", "delete"},
            "/api/v1/presentations/{presentationId}/duplicate": {"post"},
        }
        for path, expected_methods in presentation_paths.items():
            with self.subTest(path=path):
                self.assertIn(path, payload["paths"])
                self.assertEqual(expected_methods, set(payload["paths"][path]))

    def test_presentation_project_api_supports_full_owner_crud_lifecycle(self) -> None:
        tokens = self._signup_and_login()

        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Lifecycle Project",
                "total_duration_seconds": 900,
                "qa_duration_seconds": 180,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        presentation_id = create_response.json()["data"]["presentation_id"]

        list_response = self.client.get(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [project["presentation_id"] for project in list_response.json()["data"]],
            [presentation_id],
        )

        detail_response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["title"], "Lifecycle Project")

        update_response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
            json={
                "title": "Lifecycle Project Updated",
                "qa_duration_seconds": 240,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["title"], "Lifecycle Project Updated")
        self.assertEqual(update_response.json()["data"]["presentation_duration_seconds"], 660)

        duplicate_response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/duplicate",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(duplicate_response.status_code, 201)
        duplicate_payload = duplicate_response.json()["data"]
        self.assertNotEqual(duplicate_payload["presentation_id"], presentation_id)
        self.assertEqual(duplicate_payload["title"], f"Lifecycle Project Updated{PRESENTATION_DUPLICATE_TITLE_SUFFIX}")
        self.assertEqual(duplicate_payload["status"], PresentationStatus.DRAFT.value)

        delete_response = self.client.delete(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertIsNone(delete_response.json()["data"])

        deleted_detail_response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(deleted_detail_response.status_code, 404)
        self.assertEqual(deleted_detail_response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

        final_list_response = self.client.get(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(final_list_response.status_code, 200)
        self.assertEqual(
            [project["presentation_id"] for project in final_list_response.json()["data"]],
            [duplicate_payload["presentation_id"]],
        )

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

    def test_owned_presentation_service_rejects_other_user_and_soft_deleted_project(self) -> None:
        owner_tokens = self._signup_and_login(email="service-owner@example.com")
        self._signup_and_login(email="service-other@example.com")
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Service Ownership Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        with self.session_factory() as session:
            owner = session.execute(select(User).where(User.email == "service-owner@example.com")).scalar_one()
            other = session.execute(select(User).where(User.email == "service-other@example.com")).scalar_one()

            owned = get_owned_presentation_project(session, user=owner, presentation_id=presentation_id)
            self.assertEqual(owned.presentation_id, presentation_id)

            with self.assertRaises(ApiError) as other_user_error:
                get_owned_presentation_project(session, user=other, presentation_id=presentation_id)
            self.assertEqual(other_user_error.exception.code, ErrorCode.PRESENTATION_NOT_FOUND)

            owned.soft_delete()
            session.commit()

            with self.assertRaises(ApiError) as deleted_error:
                get_owned_presentation_project(session, user=owner, presentation_id=presentation_id)
            self.assertEqual(deleted_error.exception.code, ErrorCode.PRESENTATION_NOT_FOUND)

    def test_presentation_status_transition_service_persists_valid_next_status(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Status Transition Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        with self.session_factory() as session:
            user = session.execute(select(User).where(User.email == "presenter@example.com")).scalar_one()
            transitioned = transition_presentation_project_status(
                session,
                user=user,
                presentation_id=presentation_id,
                next_status=PresentationStatus.FILE_UPLOADED,
            )

        self.assertEqual(transitioned.status, PresentationStatus.FILE_UPLOADED)

        with self.session_factory() as session:
            stored = session.get(Presentation, presentation_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.status, PresentationStatus.FILE_UPLOADED)

    def test_presentation_status_transition_rejects_skipped_workflow_state(self) -> None:
        with self.assertRaises(ApiError) as context:
            validate_presentation_status_transition(
                current_status=PresentationStatus.DRAFT,
                next_status=PresentationStatus.PARSED,
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.code, ErrorCode.PRESENTATION_INVALID_STATUS_TRANSITION)
        self.assertEqual(context.exception.message, PRESENTATION_INVALID_STATUS_TRANSITION_MESSAGE)
        self.assertEqual(context.exception.details["currentStatus"], PresentationStatus.DRAFT.value)
        self.assertEqual(context.exception.details["nextStatus"], PresentationStatus.PARSED.value)
        self.assertEqual(
            context.exception.details["allowedNextStatuses"],
            [
                PresentationStatus.FAILED.value,
                PresentationStatus.FILE_UPLOADED.value,
            ],
        )

    def test_presentation_status_transition_allows_failure_from_processing_states(self) -> None:
        processing_statuses = (
            PresentationStatus.PARSING,
            PresentationStatus.ANALYZING,
            PresentationStatus.SCRIPT_GENERATING,
        )

        for current_status in processing_statuses:
            with self.subTest(current_status=current_status):
                validate_presentation_status_transition(
                    current_status=current_status,
                    next_status=PresentationStatus.FAILED,
                )

    def test_presentation_status_transition_treats_terminal_states_as_closed(self) -> None:
        self.assertEqual(
            get_allowed_presentation_status_transitions(PresentationStatus.COMPLETED),
            frozenset(),
        )
        self.assertEqual(
            get_allowed_presentation_status_transitions(PresentationStatus.FAILED),
            frozenset(),
        )

        with self.assertRaises(ApiError):
            validate_presentation_status_transition(
                current_status=PresentationStatus.COMPLETED,
                next_status=PresentationStatus.FAILED,
            )

    def test_get_presentation_requires_authentication(self) -> None:
        response = self.client.get("/api/v1/presentations/1")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_duplicate_presentation_creates_owned_draft_copy(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Original Project",
                "total_duration_seconds": 900,
                "qa_duration_seconds": 180,
            },
        )
        source_id = create_response.json()["data"]["presentation_id"]

        response = self.client.post(
            f"/api/v1/presentations/{source_id}/duplicate",
            headers=self._authorization_header(tokens),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["message"], "Created")
        self.assertNotEqual(payload["data"]["presentation_id"], source_id)
        self.assertEqual(payload["data"]["title"], f"Original Project{PRESENTATION_DUPLICATE_TITLE_SUFFIX}")
        self.assertEqual(payload["data"]["total_duration_seconds"], 900)
        self.assertEqual(payload["data"]["qa_duration_seconds"], 180)
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 720)
        self.assertEqual(payload["data"]["presentation_context"], DEFAULT_PRESENTATION_CONTEXT.value)
        self.assertEqual(payload["data"]["status"], PresentationStatus.DRAFT.value)

        with self.session_factory() as session:
            duplicate = session.get(Presentation, payload["data"]["presentation_id"])

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.user_id, 1)
        self.assertEqual(duplicate.duplicated_from_id, source_id)

    def test_duplicate_presentation_returns_not_found_for_other_user_project(self) -> None:
        owner_tokens = self._signup_and_login(email="duplicate-owner@example.com")
        other_tokens = self._signup_and_login(email="duplicate-other@example.com")
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Private Duplicate Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/duplicate",
            headers=self._authorization_header(other_tokens),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

        with self.session_factory() as session:
            presentations = session.execute(select(Presentation)).scalars().all()

        self.assertEqual(len(presentations), 1)

    def test_duplicate_presentation_returns_not_found_for_soft_deleted_project(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Deleted Duplicate Project",
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

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/duplicate",
            headers=self._authorization_header(tokens),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_duplicate_presentation_requires_authentication(self) -> None:
        response = self.client.post("/api/v1/presentations/1/duplicate")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_update_presentation_persists_editable_fields_and_recalculates_time(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Initial Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
            json={
                "title": " Updated Project ",
                "total_duration_seconds": 900,
                "qa_duration_seconds": 180,
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["title"], "Updated Project")
        self.assertEqual(payload["data"]["total_duration_seconds"], 900)
        self.assertEqual(payload["data"]["qa_duration_seconds"], 180)
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 720)
        self.assertEqual(payload["data"]["presentation_context"], DEFAULT_PRESENTATION_CONTEXT.value)
        self.assertEqual(payload["data"]["fixed_condition"]["presentation_target"], "담당 교수님")

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)

        self.assertIsNotNone(presentation)
        self.assertEqual(presentation.title, "Updated Project")
        self.assertEqual(presentation.presentation_duration_seconds, 720)

    def test_update_presentation_recalculates_time_for_partial_duration_update(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Partial Update Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
            json={"qa_duration_seconds": 240},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["total_duration_seconds"], 600)
        self.assertEqual(payload["data"]["qa_duration_seconds"], 240)
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 360)

    def test_update_presentation_returns_not_found_for_other_user_project(self) -> None:
        owner_tokens = self._signup_and_login(email="update-owner@example.com")
        other_tokens = self._signup_and_login(email="update-other@example.com")
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Private Update Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(other_tokens),
            json={"title": "Unauthorized Update"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_update_presentation_rejects_fixed_condition_request_fields(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Fixed Condition Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
            json={"presentation_target": "custom target"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.VALIDATION_ERROR.value)

    def test_update_presentation_rejects_invalid_available_presentation_time(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Invalid Update Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
            json={"qa_duration_seconds": 541},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], ErrorCode.PRESENTATION_INVALID_TIME_RANGE.value)
        self.assertEqual(payload["error"]["message"], PRESENTATION_INVALID_TIME_RANGE_MESSAGE)
        self.assertEqual(payload["error"]["details"]["reason"], "presentation_duration_too_short")

    def test_update_presentation_requires_authentication(self) -> None:
        response = self.client.patch(
            "/api/v1/presentations/1",
            json={"title": "No Auth Update"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_delete_presentation_soft_deletes_owned_project(self) -> None:
        tokens = self._signup_and_login()
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(tokens),
            json={
                "title": "Delete Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.delete(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertIsNone(payload["data"])

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)

        self.assertIsNotNone(presentation)
        self.assertIsNotNone(presentation.deleted_at)

        get_response = self.client.get(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(tokens),
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(get_response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_delete_presentation_returns_not_found_for_other_user_project(self) -> None:
        owner_tokens = self._signup_and_login(email="delete-owner@example.com")
        other_tokens = self._signup_and_login(email="delete-other@example.com")
        create_response = self.client.post(
            "/api/v1/presentations",
            headers=self._authorization_header(owner_tokens),
            json={
                "title": "Private Delete Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        presentation_id = create_response.json()["data"]["presentation_id"]

        response = self.client.delete(
            f"/api/v1/presentations/{presentation_id}",
            headers=self._authorization_header(other_tokens),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)

        self.assertIsNotNone(presentation)
        self.assertIsNone(presentation.deleted_at)

    def test_delete_presentation_requires_authentication(self) -> None:
        response = self.client.delete("/api/v1/presentations/1")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)


if __name__ == "__main__":
    unittest.main()
