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
    SlideTiming,
    User,
)
from app.services import analyze_presentation_material, create_presentation_file, create_presentation_project


class PresentationTimingApiTest(unittest.TestCase):
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
            ],
        )
        self.settings = Settings(
            app_name="Presentation Timing API Test",
            jwt_secret_key="presentation-timing-api-test-secret",
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

    def _create_analyzed_presentation(self) -> tuple[int, int, list[int]]:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="timing@example.com",
                password_hash="hash",
                name="Timing Owner",
            )
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="Timing Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )
            presentation_file = create_presentation_file(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                filename="timing.pdf",
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
                    raw_text="Short problem summary.",
                    notes_text="Brief opening.",
                ),
                Slide(
                    slide_id=2,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=2,
                    sort_order=2,
                    title="Architecture",
                    raw_text=(
                        "The backend coordinates parsing, analysis, script generation, "
                        "rehearsal media, and professor oriented feedback with multiple persistence steps."
                    ),
                    notes_text="Spend more time explaining why each backend boundary exists.",
                ),
                Slide(
                    slide_id=3,
                    presentation_id=presentation.presentation_id,
                    file_id=presentation_file.file_id,
                    slide_number=3,
                    sort_order=3,
                    title="Appendix",
                    raw_text="Backup details.",
                    excluded=True,
                ),
            ]
            session.add_all(slides)
            presentation.status = PresentationStatus.PARSED
            presentation_file.status = "PARSED"
            presentation_file.slide_count = len(slides)
            session.commit()
            analyze_presentation_material(session, user=user, presentation_id=presentation.presentation_id)
            return user.user_id, presentation.presentation_id, [slide.slide_id for slide in slides]

    def test_timing_routes_generate_read_update_and_rebalance(self) -> None:
        user_id, presentation_id, slide_ids = self._create_analyzed_presentation()
        headers = self._auth_headers(user_id)

        before = self.client.get(f"/api/v1/presentations/{presentation_id}/timings", headers=headers)
        self.assertEqual(before.status_code, 404)
        self.assertEqual(before.json()["error"]["code"], ErrorCode.TIMING_NOT_FOUND.value)

        create = self.client.post(f"/api/v1/presentations/{presentation_id}/timings/generate", headers=headers)
        payload = create.json()
        self.assertEqual(create.status_code, 202)
        self.assertEqual(payload["data"]["presentation_duration_seconds"], 480)
        self.assertEqual(payload["data"]["total_allocated_seconds"], 480)
        self.assertEqual(payload["data"]["status"], "COMPLETED")
        self.assertEqual([timing["slide_id"] for timing in payload["data"]["timings"]], slide_ids[:2])
        self.assertGreater(
            payload["data"]["timings"][1]["allocated_seconds"],
            payload["data"]["timings"][0]["allocated_seconds"],
        )

        latest = self.client.get(f"/api/v1/presentations/{presentation_id}/timings", headers=headers)
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json()["data"]["total_allocated_seconds"], 480)

        update = self.client.patch(
            f"/api/v1/presentations/{presentation_id}/timings/{slide_ids[0]}",
            headers=headers,
            json={"allocated_seconds": 180},
        )
        update_payload = update.json()
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update_payload["data"]["total_allocated_seconds"], 480)
        locked = [timing for timing in update_payload["data"]["timings"] if timing["slide_id"] == slide_ids[0]][0]
        self.assertEqual(locked["allocated_seconds"], 180)
        self.assertTrue(locked["is_locked"])

        rebalance = self.client.post(f"/api/v1/presentations/{presentation_id}/timings/rebalance", headers=headers)
        rebalance_payload = rebalance.json()
        self.assertEqual(rebalance.status_code, 202)
        self.assertEqual(rebalance_payload["data"]["total_allocated_seconds"], 480)
        self.assertEqual(
            [timing for timing in rebalance_payload["data"]["timings"] if timing["slide_id"] == slide_ids[0]][0][
                "allocated_seconds"
            ],
            180,
        )

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)
            timings = session.execute(select(SlideTiming).order_by(SlideTiming.version)).scalars().all()
            active_timings = [timing for timing in timings if timing.is_active]

        self.assertEqual(presentation.timing_status, "COMPLETED")
        self.assertEqual(sum(timing.allocated_seconds for timing in active_timings), 480)
        self.assertEqual(len(active_timings), 2)
        self.assertEqual(max(timing.version for timing in timings), 3)

    def test_timing_update_rejects_impossible_locked_duration(self) -> None:
        user_id, presentation_id, slide_ids = self._create_analyzed_presentation()
        headers = self._auth_headers(user_id)

        response = self.client.patch(
            f"/api/v1/presentations/{presentation_id}/timings/{slide_ids[0]}",
            headers=headers,
            json={"allocated_seconds": 475},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.TIMING_TOTAL_MISMATCH.value)

    def test_timing_routes_require_project_ownership(self) -> None:
        user_id, presentation_id, _slide_ids = self._create_analyzed_presentation()
        with self.session_factory() as session:
            session.add(User(user_id=2, email="other-timing@example.com", password_hash="hash", name="Other"))
            session.commit()

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/timings/generate",
            headers=self._auth_headers(2),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)
        self.assertEqual(user_id, 1)


if __name__ == "__main__":
    unittest.main()
