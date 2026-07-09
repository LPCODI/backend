import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings, create_access_token
from app.db import Base, get_db
from app.main import create_app
from app.models import Presentation, PresentationFile, RefreshToken, Slide, User
from app.services import create_presentation_file, create_presentation_project


class SlideApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.TemporaryDirectory()
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
            tables=[
                User.__table__,
                RefreshToken.__table__,
                Presentation.__table__,
                PresentationFile.__table__,
                Slide.__table__,
            ],
        )
        self.settings = Settings(
            app_name="Slide API Test",
            jwt_secret_key="slide-api-test-secret",
            local_storage_path=Path(self.storage_dir.name),
            _env_file=None,
        )
        self.app = create_app(settings=self.settings)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(
            self.engine,
            tables=[
                Slide.__table__,
                PresentationFile.__table__,
                Presentation.__table__,
                RefreshToken.__table__,
                User.__table__,
            ],
        )
        self.engine.dispose()
        self.storage_dir.cleanup()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _auth_headers(self, user_id: int) -> dict[str, str]:
        token = create_access_token(user_id=user_id, settings=self.settings)
        return {"Authorization": f"Bearer {token}"}

    def _create_project_file_and_slides(self) -> tuple[User, int, int, list[int]]:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="slides@example.com",
                password_hash="hash",
                name="Slide Owner",
            )
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="Slide Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )
            presentation_file = create_presentation_file(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                filename="slides.pdf",
                content_type="application/pdf",
                content=b"%PDF-1.4 fake",
                settings=self.settings,
            )
            slides = [
                Slide(
                    slide_id=1,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=1,
                    sort_order=1,
                    title="Problem",
                    raw_text="Problem body",
                    notes_text="Explain motivation.",
                ),
                Slide(
                    slide_id=2,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=2,
                    sort_order=2,
                    title="Solution",
                    raw_text="Solution body",
                ),
                Slide(
                    slide_id=3,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=3,
                    sort_order=3,
                    title="Demo",
                    raw_text="Demo body",
                ),
            ]
            session.add_all(slides)
            session.commit()
            return user, presentation.presentation_id, presentation_file.file_id, [slide.slide_id for slide in slides]

    def test_slide_routes_list_get_update_exclude_and_include(self) -> None:
        user, presentation_id, _file_id, slide_ids = self._create_project_file_and_slides()
        headers = self._auth_headers(user.user_id)

        list_response = self.client.get(f"/api/v1/presentations/{presentation_id}/slides", headers=headers)
        list_payload = list_response.json()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([slide["title"] for slide in list_payload["data"]], ["Problem", "Solution", "Demo"])

        detail_response = self.client.get(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[0]}",
            headers=headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["notes_text"], "Explain motivation.")

        update_response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[0]}",
            headers=headers,
            json={
                "title": "Updated Problem",
                "raw_text": "Updated body",
                "notes_text": None,
                "image_url": "https://example.test/slide-1.png",
            },
        )
        update_payload = update_response.json()
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_payload["data"]["title"], "Updated Problem")
        self.assertEqual(update_payload["data"]["raw_text"], "Updated body")
        self.assertIsNone(update_payload["data"]["notes_text"])
        self.assertEqual(update_payload["data"]["image_url"], "https://example.test/slide-1.png")

        exclude_response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[1]}/exclude",
            headers=headers,
        )
        self.assertEqual(exclude_response.status_code, 200)
        self.assertTrue(exclude_response.json()["data"]["excluded"])

        include_response = self.client.delete(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[1]}/exclude",
            headers=headers,
        )
        self.assertEqual(include_response.status_code, 200)
        self.assertFalse(include_response.json()["data"]["excluded"])

        with self.session_factory() as session:
            updated_slide = session.get(Slide, slide_ids[0])
            included_slide = session.get(Slide, slide_ids[1])

        self.assertEqual(updated_slide.title, "Updated Problem")
        self.assertIsNone(updated_slide.notes_text)
        self.assertFalse(included_slide.excluded)

    def test_slide_order_route_replaces_sort_order(self) -> None:
        user, presentation_id, _file_id, slide_ids = self._create_project_file_and_slides()
        headers = self._auth_headers(user.user_id)

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}/slides/order",
            headers=headers,
            json={"slide_ids": [slide_ids[2], slide_ids[0], slide_ids[1]]},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([slide["slide_id"] for slide in payload["data"]], [slide_ids[2], slide_ids[0], slide_ids[1]])
        self.assertEqual([slide["sort_order"] for slide in payload["data"]], [1, 2, 3])

        with self.session_factory() as session:
            slides = session.execute(select(Slide).order_by(Slide.sort_order)).scalars().all()

        self.assertEqual([slide.slide_id for slide in slides], [slide_ids[2], slide_ids[0], slide_ids[1]])

    def test_slide_order_route_rejects_missing_or_foreign_slide_ids(self) -> None:
        user, presentation_id, _file_id, slide_ids = self._create_project_file_and_slides()
        headers = self._auth_headers(user.user_id)

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}/slides/order",
            headers=headers,
            json={"slide_ids": [slide_ids[0], slide_ids[1]]},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], "SLIDE_INVALID_ORDER")
        self.assertEqual(payload["error"]["details"]["expectedSlideIds"], slide_ids)

    def test_slide_routes_require_project_ownership(self) -> None:
        user, presentation_id, _file_id, slide_ids = self._create_project_file_and_slides()
        with self.session_factory() as session:
            session.add(
                User(
                    user_id=2,
                    email="other-slides@example.com",
                    password_hash="hash",
                    name="Other",
                )
            )
            session.commit()

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[0]}",
            headers=self._auth_headers(2),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PRESENTATION_NOT_FOUND")
        self.assertEqual(user.user_id, 1)


if __name__ == "__main__":
    unittest.main()
