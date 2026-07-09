import asyncio
import tempfile
import unittest
from collections.abc import Generator
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import ApiError, Settings, create_access_token
from app.db import Base, get_db
from app.domain import ErrorCode, PresentationStatus
from app.main import create_app
from app.models import Presentation, PresentationFile, RefreshToken, Slide, User
from app.services import (
    AnalysisInput,
    DocumentParseResult,
    create_presentation_file,
    create_presentation_project,
    parse_presentation_file,
)


class FakeDocumentParser:
    provider = "fake-parser"
    version = "test"

    async def parse(self, source: AnalysisInput) -> DocumentParseResult:
        self.source = source
        return DocumentParseResult(
            provider=self.provider,
            version=self.version,
            slides=(
                {
                    "slideNumber": 1,
                    "sortOrder": 1,
                    "title": "Problem",
                    "body": "Existing practice tools stop at recording.",
                    "rawText": "Problem\n\nExisting practice tools stop at recording.",
                    "notes": "Explain project motivation.",
                },
                {
                    "slideNumber": 2,
                    "sortOrder": 2,
                    "title": "Solution",
                    "body": "AI feedback closes the loop.",
                    "rawText": "Solution\n\nAI feedback closes the loop.",
                    "notes": None,
                },
            ),
            warnings=("stub warning",),
        )


class FailingDocumentParser:
    async def parse(self, source: AnalysisInput) -> DocumentParseResult:
        del source
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE,
            message="파싱 실패",
        )


class PresentationParseApiTest(unittest.TestCase):
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
            app_name="Presentation Parse API Test",
            jwt_secret_key="presentation-parse-api-test-secret",
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

    def _create_user_presentation_and_file(self) -> tuple[User, int, int]:
        with self.session_factory() as session:
            user = User(
                user_id=1,
                email="parse@example.com",
                password_hash="hash",
                name="Parser",
            )
            session.add(user)
            session.commit()
            presentation = create_presentation_project(
                session,
                user=user,
                title="Parse Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
            )
            presentation_file = create_presentation_file(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                filename="demo.pdf",
                content_type="application/pdf",
                content=b"%PDF-1.4 fake",
                settings=self.settings,
            )
            return user, presentation.presentation_id, presentation_file.file_id

    def _auth_headers(self, user_id: int) -> dict[str, str]:
        token = create_access_token(user_id=user_id, settings=self.settings)
        return {"Authorization": f"Bearer {token}"}

    def test_parse_presentation_file_persists_slides_and_statuses(self) -> None:
        user, presentation_id, file_id = self._create_user_presentation_and_file()
        parser = FakeDocumentParser()

        with self.session_factory() as session:
            summary = asyncio.run(
                parse_presentation_file(
                    session,
                    user=user,
                    presentation_id=presentation_id,
                    file_id=file_id,
                    settings=self.settings,
                    parser=parser,
                )
            )

            slides = session.execute(select(Slide).order_by(Slide.sort_order)).scalars().all()
            presentation = session.get(Presentation, presentation_id)
            presentation_file = session.get(PresentationFile, file_id)

        self.assertEqual(summary.presentation_id, presentation_id)
        self.assertEqual(summary.file_id, file_id)
        self.assertEqual(summary.status, "PARSED")
        self.assertEqual(summary.slide_count, 2)
        self.assertEqual(summary.parser_provider, "fake-parser")
        self.assertEqual(summary.warnings, ("stub warning",))
        self.assertEqual(parser.source.file_path, Path(self.storage_dir.name) / presentation_file.object_key)
        self.assertEqual(presentation.status, PresentationStatus.PARSED.value)
        self.assertEqual(presentation_file.status, "PARSED")
        self.assertEqual(presentation_file.slide_count, 2)
        self.assertIsNotNone(presentation_file.parsed_at)
        self.assertEqual([slide.title for slide in slides], ["Problem", "Solution"])
        self.assertEqual(slides[0].notes_text, "Explain project motivation.")
        self.assertIn("Existing practice tools", slides[0].raw_text)

    def test_parse_failure_persists_failed_state(self) -> None:
        user, presentation_id, file_id = self._create_user_presentation_and_file()

        with self.session_factory() as session:
            with self.assertRaises(ApiError):
                asyncio.run(
                    parse_presentation_file(
                        session,
                        user=user,
                        presentation_id=presentation_id,
                        file_id=file_id,
                        settings=self.settings,
                        parser=FailingDocumentParser(),
                    )
                )

            presentation = session.get(Presentation, presentation_id)
            presentation_file = session.get(PresentationFile, file_id)
            slides = session.execute(select(Slide)).scalars().all()

        self.assertEqual(presentation.status, PresentationStatus.FAILED.value)
        self.assertEqual(presentation_file.status, "FAILED")
        self.assertEqual(presentation_file.parse_error_message, "파싱 실패")
        self.assertEqual(slides, [])

    def test_parse_result_route_returns_latest_file_and_persisted_slides(self) -> None:
        user, presentation_id, file_id = self._create_user_presentation_and_file()
        with self.session_factory() as session:
            asyncio.run(
                parse_presentation_file(
                    session,
                    user=user,
                    presentation_id=presentation_id,
                    file_id=file_id,
                    settings=self.settings,
                    parser=FakeDocumentParser(),
                )
            )

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}/parse-result",
            headers=self._auth_headers(user.user_id),
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["presentation_id"], presentation_id)
        self.assertEqual(payload["data"]["file"]["file_id"], file_id)
        self.assertEqual(payload["data"]["file"]["status"], "PARSED")
        self.assertEqual(payload["data"]["slide_count"], 2)
        self.assertEqual([slide["title"] for slide in payload["data"]["slides"]], ["Problem", "Solution"])
        self.assertEqual(payload["data"]["slides"][0]["slide_number"], 1)
        self.assertEqual(payload["data"]["slides"][0]["sort_order"], 1)
        self.assertEqual(payload["data"]["slides"][0]["notes_text"], "Explain project motivation.")
        self.assertIn("Existing practice tools", payload["data"]["slides"][0]["raw_text"])

    def test_parse_result_route_requires_project_ownership(self) -> None:
        user, presentation_id, file_id = self._create_user_presentation_and_file()
        with self.session_factory() as session:
            other_user = User(
                user_id=2,
                email="other-parser@example.com",
                password_hash="hash",
                name="Other Parser",
            )
            session.add(other_user)
            session.commit()
            asyncio.run(
                parse_presentation_file(
                    session,
                    user=user,
                    presentation_id=presentation_id,
                    file_id=file_id,
                    settings=self.settings,
                    parser=FakeDocumentParser(),
                )
            )

        response = self.client.get(
            f"/api/v1/presentations/{presentation_id}/parse-result",
            headers=self._auth_headers(2),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_parse_route_is_exposed_in_openapi(self) -> None:
        response = self.client.get("/openapi.json")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        path = payload["paths"]["/api/v1/presentations/{presentationId}/parse"]
        self.assertEqual(set(path), {"post"})
        self.assertIn("202", path["post"]["responses"])
        parse_result_path = payload["paths"]["/api/v1/presentations/{presentationId}/parse-result"]
        self.assertEqual(set(parse_result_path), {"get"})
        self.assertIn("200", parse_result_path["get"]["responses"])


if __name__ == "__main__":
    unittest.main()
