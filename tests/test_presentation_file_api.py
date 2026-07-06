import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Settings
from app.db import Base, get_db
from app.domain import ErrorCode, PresentationStatus
from app.main import create_app
from app.models import Presentation, PresentationFile, RefreshToken, User


class PresentationFileApiTest(unittest.TestCase):
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
            ],
        )
        self.settings = Settings(
            app_name="Presentation File API Test",
            jwt_secret_key="presentation-file-api-test-secret",
            local_storage_path=Path(self.storage_dir.name),
            max_presentation_file_size_bytes=1024,
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

    def _signup_login_and_create_presentation(self, *, email: str = "presenter@example.com") -> tuple[dict[str, str], int]:
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
        tokens = login.json()["data"]
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        create = self.client.post(
            "/api/v1/presentations",
            headers=headers,
            json={
                "title": "Upload Project",
                "total_duration_seconds": 600,
                "qa_duration_seconds": 120,
            },
        )
        self.assertEqual(create.status_code, 201)
        return headers, create.json()["data"]["presentation_id"]

    def test_upload_list_and_delete_presentation_file(self) -> None:
        headers, presentation_id = self._signup_login_and_create_presentation()

        upload = self.client.post(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=headers,
            files={"file": ("demo.pdf", b"%PDF-1.4 demo", "application/pdf")},
        )
        upload_payload = upload.json()

        self.assertEqual(upload.status_code, 201)
        self.assertTrue(upload_payload["success"])
        self.assertEqual(upload_payload["message"], "Created")
        self.assertEqual(upload_payload["data"]["original_filename"], "demo.pdf")
        self.assertEqual(upload_payload["data"]["file_type"], "PDF")
        self.assertEqual(upload_payload["data"]["mime_type"], "application/pdf")
        self.assertEqual(upload_payload["data"]["file_size_bytes"], len(b"%PDF-1.4 demo"))
        self.assertEqual(upload_payload["data"]["status"], "UPLOADED")
        file_id = upload_payload["data"]["file_id"]
        object_key = upload_payload["data"]["object_key"]
        self.assertTrue((Path(self.storage_dir.name) / object_key).exists())

        list_response = self.client.get(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([file["file_id"] for file in list_response.json()["data"]], [file_id])

        delete_response = self.client.delete(
            f"/api/v1/presentations/{presentation_id}/files/{file_id}",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertIsNone(delete_response.json()["data"])
        self.assertFalse((Path(self.storage_dir.name) / object_key).exists())

        with self.session_factory() as session:
            presentation = session.get(Presentation, presentation_id)
            presentation_file = session.get(PresentationFile, file_id)

        self.assertEqual(presentation.status, PresentationStatus.FILE_UPLOADED.value)
        self.assertIsNotNone(presentation_file.deleted_at)

    def test_upload_rejects_unsupported_extension_and_mime_type(self) -> None:
        headers, presentation_id = self._signup_login_and_create_presentation()

        unsupported_extension = self.client.post(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=headers,
            files={"file": ("demo.txt", b"text", "text/plain")},
        )
        unsupported_mime = self.client.post(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=headers,
            files={"file": ("demo.pdf", b"%PDF-1.4", "text/plain")},
        )

        self.assertEqual(unsupported_extension.status_code, 400)
        self.assertEqual(
            unsupported_extension.json()["error"]["code"],
            ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE.value,
        )
        self.assertEqual(unsupported_mime.status_code, 400)
        self.assertEqual(
            unsupported_mime.json()["error"]["code"],
            ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE.value,
        )

    def test_upload_rejects_file_larger_than_configured_limit(self) -> None:
        headers, presentation_id = self._signup_login_and_create_presentation()

        response = self.client.post(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=headers,
            files={"file": ("demo.pdf", b"x" * 1025, "application/pdf")},
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], ErrorCode.PRESENTATION_FILE_TOO_LARGE.value)

        with self.session_factory() as session:
            self.assertEqual(session.execute(select(PresentationFile)).scalars().all(), [])

    def test_presentation_file_api_requires_project_ownership(self) -> None:
        first_headers, presentation_id = self._signup_login_and_create_presentation(email="first@example.com")
        second_headers, _ = self._signup_login_and_create_presentation(email="second@example.com")

        first_upload = self.client.post(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=first_headers,
            files={"file": ("demo.pdf", b"%PDF-1.4 demo", "application/pdf")},
        )
        self.assertEqual(first_upload.status_code, 201)
        file_id = first_upload.json()["data"]["file_id"]

        second_list = self.client.get(
            f"/api/v1/presentations/{presentation_id}/files",
            headers=second_headers,
        )
        second_delete = self.client.delete(
            f"/api/v1/presentations/{presentation_id}/files/{file_id}",
            headers=second_headers,
        )

        self.assertEqual(second_list.status_code, 404)
        self.assertEqual(second_list.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)
        self.assertEqual(second_delete.status_code, 404)
        self.assertEqual(second_delete.json()["error"]["code"], ErrorCode.PRESENTATION_NOT_FOUND.value)

    def test_presentation_file_routes_are_exposed_in_openapi(self) -> None:
        response = self.client.get("/openapi.json")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {"get", "post"},
            set(payload["paths"]["/api/v1/presentations/{presentationId}/files"]),
        )
        self.assertEqual(
            {"delete"},
            set(payload["paths"]["/api/v1/presentations/{presentationId}/files/{fileId}"]),
        )


if __name__ == "__main__":
    unittest.main()
