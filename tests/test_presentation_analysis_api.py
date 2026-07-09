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
from app.domain import ErrorCode, PresentationStatus
from app.main import create_app
from app.models import Presentation, PresentationAnalysis, PresentationFile, RefreshToken, Slide, SlideAnalysis, User
from app.services import create_presentation_file, create_presentation_project


class PresentationAnalysisApiTest(unittest.TestCase):
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
                PresentationAnalysis.__table__,
                SlideAnalysis.__table__,
            ],
        )
        self.settings = Settings(
            app_name="Presentation Analysis API Test",
            jwt_secret_key="presentation-analysis-api-test-secret",
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
                SlideAnalysis.__table__,
                PresentationAnalysis.__table__,
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

    def _create_parsed_presentation(self) -> tuple[int, int, list[int]]:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="analysis@example.com",
                password_hash="hash",
                name="Analysis Owner",
            )
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="AI Speech Coach",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )
            presentation_file = create_presentation_file(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                filename="analysis.pdf",
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
                    raw_text="Current presentation practice tools only record rehearsals without professor questions.",
                    notes_text="Explain why existing tools miss the university project context.",
                ),
                Slide(
                    slide_id=2,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=2,
                    sort_order=2,
                    title="Solution",
                    raw_text="AI analysis extracts core messages, keywords, weak explanations, and likely questions.",
                    notes_text="Connect the backend analysis result to the mobile preparation flow.",
                ),
                Slide(
                    slide_id=3,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=3,
                    sort_order=3,
                    title="Appendix",
                    raw_text="Backup implementation detail.",
                    excluded=True,
                ),
            ]
            session.add_all(slides)
            presentation.status = PresentationStatus.PARSED
            presentation_file.status = "PARSED"
            presentation_file.slide_count = len(slides)
            session.commit()
            return user.user_id, presentation.presentation_id, [slide.slide_id for slide in slides]

    def test_analysis_routes_create_read_slide_result_and_regenerate_versions(self) -> None:
        user_id, presentation_id, slide_ids = self._create_parsed_presentation()
        headers = self._auth_headers(user_id)

        before = self.client.get(f"/api/v1/presentations/{presentation_id}/analysis", headers=headers)
        self.assertEqual(before.status_code, 404)
        self.assertEqual(before.json()["error"]["code"], ErrorCode.ANALYSIS_NOT_FOUND.value)

        create = self.client.post(f"/api/v1/presentations/{presentation_id}/analysis", headers=headers)
        create_payload = create.json()
        self.assertEqual(create.status_code, 202)
        self.assertEqual(create_payload["data"]["version"], 1)
        self.assertEqual(create_payload["data"]["status"], "COMPLETED")
        self.assertEqual(create_payload["data"]["model_name"], "deterministic-mvp-slide-analysis")
        self.assertEqual(len(create_payload["data"]["slide_analyses"]), 2)
        self.assertEqual(
            [analysis["slide_id"] for analysis in create_payload["data"]["slide_analyses"]],
            slide_ids[:2],
        )
        self.assertTrue(create_payload["data"]["professor_question_points"])

        latest = self.client.get(f"/api/v1/presentations/{presentation_id}/analysis", headers=headers)
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json()["data"]["presentation_analysis_id"], create_payload["data"]["presentation_analysis_id"])

        slide = self.client.get(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[0]}/analysis",
            headers=headers,
        )
        slide_payload = slide.json()
        self.assertEqual(slide.status_code, 200)
        self.assertEqual(slide_payload["data"]["slide_id"], slide_ids[0])
        self.assertIn("Problem", slide_payload["data"]["core_message"])
        self.assertTrue(slide_payload["data"]["keywords"])

        excluded_slide = self.client.get(
            f"/api/v1/presentations/{presentation_id}/slides/{slide_ids[2]}/analysis",
            headers=headers,
        )
        self.assertEqual(excluded_slide.status_code, 404)
        self.assertEqual(excluded_slide.json()["error"]["code"], ErrorCode.ANALYSIS_NOT_FOUND.value)

        regenerate = self.client.post(
            f"/api/v1/presentations/{presentation_id}/analysis/regenerate",
            headers=headers,
        )
        regenerate_payload = regenerate.json()
        self.assertEqual(regenerate.status_code, 202)
        self.assertEqual(regenerate_payload["data"]["version"], 2)
        self.assertEqual(len(regenerate_payload["data"]["slide_analyses"]), 2)

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)
            analyses = session.execute(
                select(PresentationAnalysis).order_by(PresentationAnalysis.version)
            ).scalars().all()
            slide_analyses = session.execute(select(SlideAnalysis)).scalars().all()

        self.assertEqual(presentation.status, PresentationStatus.ANALYZED.value)
        self.assertEqual([analysis.version for analysis in analyses], [1, 2])
        self.assertEqual(len(slide_analyses), 4)

    def test_analysis_route_rejects_presentation_without_parsed_slides(self) -> None:
        with self.session_factory() as session:
            user = User(user_id=1, email="empty@example.com", password_hash="hash", name="Empty")
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="Empty",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )

        response = self.client.post(
            f"/api/v1/presentations/{presentation.presentation_id}/analysis",
            headers=self._auth_headers(1),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.ANALYSIS_NOT_READY.value)


if __name__ == "__main__":
    unittest.main()
