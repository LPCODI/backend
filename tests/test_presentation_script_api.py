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
from app.models import (
    Presentation,
    PresentationAnalysis,
    PresentationFile,
    RefreshToken,
    Slide,
    SlideAnalysis,
    SlideScript,
    SlideTiming,
    User,
)
from app.services import (
    analyze_presentation_material,
    create_presentation_file,
    create_presentation_project,
    generate_presentation_timings,
)


class PresentationScriptApiTest(unittest.TestCase):
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
                SlideTiming.__table__,
                SlideScript.__table__,
            ],
        )
        self.settings = Settings(
            app_name="Presentation Script API Test",
            jwt_secret_key="presentation-script-api-test-secret",
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
                SlideScript.__table__,
                SlideTiming.__table__,
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

    def _create_timed_presentation(self) -> tuple[int, int, list[int]]:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="script-api@example.com",
                password_hash="hash",
                name="Script API Owner",
            )
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="Script API Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )
            presentation_file = create_presentation_file(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                filename="script-api.pdf",
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
                    raw_text="기존 발표 연습은 시간 관리와 피드백이 분리되어 있습니다.",
                    notes_text="교수님께 문제 정의를 먼저 설명합니다.",
                ),
                Slide(
                    slide_id=2,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=2,
                    sort_order=2,
                    title="Architecture",
                    raw_text="FastAPI 백엔드는 자료 분석, 시간 배분, 대본 생성을 연결합니다.",
                    notes_text="서비스 경계와 저장 흐름을 강조합니다.",
                ),
                Slide(
                    slide_id=3,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=3,
                    sort_order=3,
                    title="Appendix",
                    raw_text="백업 슬라이드입니다.",
                    excluded=True,
                ),
            ]
            session.add_all(slides)
            presentation.status = PresentationStatus.PARSED
            presentation_file.status = "PARSED"
            presentation_file.slide_count = len(slides)
            session.commit()
            analyze_presentation_material(session, user=user, presentation_id=presentation.presentation_id)
            generate_presentation_timings(session, user=user, presentation_id=presentation.presentation_id)
            return user.user_id, presentation.presentation_id, [slide.slide_id for slide in slides]

    def test_generate_scripts_persists_active_professor_scripts(self) -> None:
        user_id, presentation_id, slide_ids = self._create_timed_presentation()

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/scripts/generate",
            headers=self._auth_headers(user_id),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(payload["data"]["presentation_id"], presentation_id)
        self.assertEqual(payload["data"]["status"], "COMPLETED")
        self.assertEqual([script["slide_id"] for script in payload["data"]["scripts"]], slide_ids[:2])
        self.assertIn("교수님", payload["data"]["scripts"][0]["script_text"])
        self.assertEqual(payload["data"]["scripts"][0]["generation_type"], "AI")
        self.assertGreater(payload["data"]["scripts"][0]["estimated_seconds"], 0)
        self.assertNotIn(slide_ids[2], [script["slide_id"] for script in payload["data"]["scripts"]])

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)
            scripts = session.execute(select(SlideScript).order_by(SlideScript.slide_id)).scalars().all()

        self.assertEqual(presentation.script_status, "COMPLETED")
        self.assertEqual(len(scripts), 2)
        self.assertTrue(all(script.is_active for script in scripts))
        self.assertEqual(sum(script.estimated_seconds or 0 for script in scripts), 480)

    def test_generate_scripts_requires_project_ownership(self) -> None:
        _user_id, presentation_id, _slide_ids = self._create_timed_presentation()
        with self.session_factory() as session:
            session.add(User(user_id=2, email="other-script@example.com", password_hash="hash", name="Other"))
            session.commit()

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/scripts/generate",
            headers=self._auth_headers(2),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)


if __name__ == "__main__":
    unittest.main()
