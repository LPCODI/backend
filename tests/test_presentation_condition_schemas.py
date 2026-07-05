import unittest
from datetime import UTC, datetime

from pydantic import ValidationError

from app.domain import DEFAULT_PRESENTATION_CONTEXT, EXCLUDED_PRESENTATION_CONDITION_FIELDS, FIXED_PRESENTATION_CONDITION
from app.schemas import (
    FixedPresentationConditionResponse,
    PresentationCreateRequest,
    PresentationResponse,
    PresentationUpdateRequest,
)


class PresentationConditionSchemaTest(unittest.TestCase):
    def test_create_request_accepts_only_editable_project_fields(self) -> None:
        request = PresentationCreateRequest(
            title="AI Speech Demo",
            total_duration_seconds=600,
            qa_duration_seconds=120,
        )

        self.assertEqual(request.title, "AI Speech Demo")
        create_fields = set(PresentationCreateRequest.model_fields)
        self.assertEqual(create_fields, {"title", "total_duration_seconds", "qa_duration_seconds"})
        self.assertFalse(set(EXCLUDED_PRESENTATION_CONDITION_FIELDS) & create_fields)

    def test_create_request_rejects_custom_presentation_condition_fields(self) -> None:
        for field_name in EXCLUDED_PRESENTATION_CONDITION_FIELDS:
            with self.subTest(field=field_name):
                payload = {
                    "title": "AI Speech Demo",
                    "total_duration_seconds": 600,
                    "qa_duration_seconds": 120,
                    field_name: "custom value",
                }
                with self.assertRaises(ValidationError):
                    PresentationCreateRequest.model_validate(payload)

    def test_update_request_rejects_custom_presentation_condition_fields(self) -> None:
        for field_name in EXCLUDED_PRESENTATION_CONDITION_FIELDS:
            with self.subTest(field=field_name):
                with self.assertRaises(ValidationError):
                    PresentationUpdateRequest.model_validate({field_name: "custom value"})

    def test_fixed_condition_response_matches_product_scope(self) -> None:
        response = FixedPresentationConditionResponse()

        self.assertEqual(response.presentation_context, DEFAULT_PRESENTATION_CONTEXT)
        self.assertEqual(
            response.model_dump(mode="json"),
            dict(FIXED_PRESENTATION_CONDITION),
        )

    def test_presentation_response_exposes_fixed_condition_without_request_input(self) -> None:
        now = datetime(2026, 7, 5, tzinfo=UTC)
        response = PresentationResponse(
            presentation_id=1,
            title="AI Speech Demo",
            total_duration_seconds=600,
            qa_duration_seconds=120,
            presentation_duration_seconds=480,
            status="DRAFT",
            created_at=now,
            updated_at=now,
        )

        self.assertEqual(response.presentation_context, DEFAULT_PRESENTATION_CONTEXT)
        self.assertEqual(response.fixed_condition.presentation_target, "담당 교수님")


if __name__ == "__main__":
    unittest.main()
