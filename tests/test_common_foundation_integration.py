import unittest

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core import (
    API_VERSION,
    REQUEST_VALIDATION_ERROR_CODE,
    REQUEST_VALIDATION_ERROR_MESSAGE,
    Settings,
)
from app.domain import AgentType, JobStatus, PresentationStatus, RehearsalStatus
from app.main import create_app
from app.schemas import DEFAULT_SUCCESS_MESSAGE, SuccessResponse


class FoundationProbeRequest(BaseModel):
    title: str = Field(min_length=1)


class FoundationProbePayload(BaseModel):
    presentation_status: PresentationStatus
    job_status: JobStatus
    rehearsal_status: RehearsalStatus
    agent_type: AgentType


class CommonFoundationIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        router = APIRouter()

        @router.post("/foundation-probe")
        def foundation_probe(
            request: FoundationProbeRequest,
        ) -> SuccessResponse[FoundationProbePayload]:
            del request
            return SuccessResponse(
                data=FoundationProbePayload(
                    presentation_status=PresentationStatus.DRAFT,
                    job_status=JobStatus.QUEUED,
                    rehearsal_status=RehearsalStatus.CREATED,
                    agent_type=AgentType.PROFESSOR,
                )
            )

        settings = Settings(
            app_name="Foundation Integration Probe",
            api_v1_prefix="/api/v1",
            cors_origins=("http://localhost:8081",),
            _env_file=None,
        )
        self.client = TestClient(create_app(settings=settings, api_v1_router=router))

    def test_docs_and_openapi_are_exposed_with_api_metadata(self) -> None:
        docs_response = self.client.get("/docs")
        schema_response = self.client.get("/openapi.json")
        schema = schema_response.json()

        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(schema["info"]["title"], "Foundation Integration Probe")
        self.assertEqual(schema["info"]["version"], API_VERSION)
        self.assertIn("/api/v1/foundation-probe", schema["paths"])

    def test_api_v1_prefix_cors_success_response_and_enum_serialization(self) -> None:
        cors_response = self.client.options(
            "/api/v1/foundation-probe",
            headers={
                "Origin": "http://localhost:8081",
                "Access-Control-Request-Method": "POST",
            },
        )
        response = self.client.post("/api/v1/foundation-probe", json={"title": "Demo"})
        payload = response.json()

        self.assertEqual(cors_response.status_code, 200)
        self.assertEqual(
            cors_response.headers["access-control-allow-origin"],
            "http://localhost:8081",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["message"], DEFAULT_SUCCESS_MESSAGE)
        self.assertEqual(
            payload["data"],
            {
                "presentation_status": "DRAFT",
                "job_status": "QUEUED",
                "rehearsal_status": "CREATED",
                "agent_type": "PROFESSOR",
            },
        )
        self.assertIn("timestamp", payload)
        self.assertEqual(self.client.post("/foundation-probe", json={"title": "Demo"}).status_code, 404)

    def test_request_validation_errors_use_common_failure_response(self) -> None:
        response = self.client.post("/api/v1/foundation-probe", json={"title": ""})
        payload = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], REQUEST_VALIDATION_ERROR_CODE)
        self.assertEqual(payload["error"]["message"], REQUEST_VALIDATION_ERROR_MESSAGE)
        self.assertEqual(payload["error"]["details"]["errors"][0]["loc"], ["body", "title"])
        self.assertIn("timestamp", payload)


if __name__ == "__main__":
    unittest.main()
