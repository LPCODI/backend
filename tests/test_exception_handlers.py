import unittest

from fastapi import APIRouter, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core import (
    HTTP_EXCEPTION_ERROR_CODE,
    INTERNAL_SERVER_ERROR_CODE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    REQUEST_VALIDATION_ERROR_CODE,
    REQUEST_VALIDATION_ERROR_MESSAGE,
    Settings,
)
from app.main import create_app


class ValidationProbeRequest(BaseModel):
    title: str = Field(min_length=1)
    total_minutes: int = Field(gt=0)


class ExceptionHandlersTest(unittest.TestCase):
    def test_http_exception_uses_common_failure_response(self) -> None:
        router = APIRouter()

        @router.get("/exception-probe")
        def exception_probe() -> None:
            raise HTTPException(status_code=404, detail="발표 프로젝트를 찾을 수 없습니다.")

        test_app = create_app(
            settings=Settings(_env_file=None),
            api_v1_router=router,
        )
        response = TestClient(test_app).get("/api/v1/exception-probe")
        payload = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], HTTP_EXCEPTION_ERROR_CODE)
        self.assertEqual(payload["error"]["message"], "발표 프로젝트를 찾을 수 없습니다.")
        self.assertIsNone(payload["error"]["details"])
        self.assertIn("timestamp", payload)

    def test_unhandled_exception_uses_common_failure_response(self) -> None:
        router = APIRouter()

        @router.get("/server-error-probe")
        def server_error_probe() -> None:
            raise RuntimeError("raw implementation detail")

        test_app = create_app(
            settings=Settings(_env_file=None),
            api_v1_router=router,
        )
        response = TestClient(test_app, raise_server_exceptions=False).get(
            "/api/v1/server-error-probe"
        )
        payload = response.json()

        self.assertEqual(response.status_code, 500)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], INTERNAL_SERVER_ERROR_CODE)
        self.assertEqual(payload["error"]["message"], INTERNAL_SERVER_ERROR_MESSAGE)
        self.assertIsNone(payload["error"]["details"])
        self.assertIn("timestamp", payload)

    def test_request_body_validation_error_uses_common_failure_response(self) -> None:
        router = APIRouter()

        @router.post("/validation-probe")
        def validation_probe(request: ValidationProbeRequest) -> dict[str, str]:
            del request
            return {"status": "ok"}

        test_app = create_app(
            settings=Settings(_env_file=None),
            api_v1_router=router,
        )
        response = TestClient(test_app).post(
            "/api/v1/validation-probe",
            json={"title": "", "total_minutes": 0},
        )
        payload = response.json()
        errors = payload["error"]["details"]["errors"]

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], REQUEST_VALIDATION_ERROR_CODE)
        self.assertEqual(payload["error"]["message"], REQUEST_VALIDATION_ERROR_MESSAGE)
        self.assertIn("timestamp", payload)
        self.assertEqual(errors[0]["loc"], ["body", "title"])
        self.assertEqual(errors[1]["loc"], ["body", "total_minutes"])

    def test_request_query_validation_error_uses_common_failure_response(self) -> None:
        router = APIRouter()

        @router.get("/query-validation-probe")
        def query_validation_probe(page: int = Query(ge=1)) -> dict[str, int]:
            return {"page": page}

        test_app = create_app(
            settings=Settings(_env_file=None),
            api_v1_router=router,
        )
        response = TestClient(test_app).get("/api/v1/query-validation-probe?page=0")
        payload = response.json()
        errors = payload["error"]["details"]["errors"]

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], REQUEST_VALIDATION_ERROR_CODE)
        self.assertEqual(payload["error"]["message"], REQUEST_VALIDATION_ERROR_MESSAGE)
        self.assertEqual(errors[0]["loc"], ["query", "page"])


if __name__ == "__main__":
    unittest.main()
