import unittest
from datetime import datetime

from pydantic import ValidationError

from app.schemas import (
    DEFAULT_ERROR_MESSAGE,
    ERROR_PAYLOAD_FIELDS,
    FAILURE_RESPONSE_FIELDS,
    ErrorPayload,
    FailureResponse,
)


class FailureResponseSchemaTest(unittest.TestCase):
    def test_failure_response_wraps_error_payload(self) -> None:
        response = FailureResponse(
            error=ErrorPayload(code="PRESENTATION_NOT_FOUND")
        )

        self.assertFalse(response.success)
        self.assertEqual(response.error.code, "PRESENTATION_NOT_FOUND")
        self.assertEqual(response.error.message, DEFAULT_ERROR_MESSAGE)
        self.assertIsNone(response.error.details)
        self.assertIsInstance(response.timestamp, datetime)

    def test_failure_response_accepts_structured_details(self) -> None:
        response = FailureResponse(
            error=ErrorPayload(
                code="VALIDATION_FAILED",
                message="요청 값이 올바르지 않습니다.",
                details={"field": "title", "reason": "required"},
            )
        )

        payload = response.model_dump(mode="json")

        self.assertEqual(payload["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(payload["error"]["details"]["field"], "title")
        self.assertIsInstance(payload["timestamp"], str)

    def test_failure_response_fields_are_fixed_in_contract_order(self) -> None:
        response = FailureResponse(error=ErrorPayload(code="UNKNOWN_ERROR"))

        self.assertEqual(
            list(response.model_dump(mode="json")),
            list(FAILURE_RESPONSE_FIELDS),
        )
        self.assertEqual(
            list(response.model_dump(mode="json")["error"]),
            list(ERROR_PAYLOAD_FIELDS),
        )
        self.assertEqual(list(FailureResponse.model_fields), list(FAILURE_RESPONSE_FIELDS))
        self.assertEqual(list(ErrorPayload.model_fields), list(ERROR_PAYLOAD_FIELDS))

    def test_failure_response_rejects_extra_fields(self) -> None:
        with self.assertRaises(ValidationError) as context:
            FailureResponse(
                error=ErrorPayload(code="UNKNOWN_ERROR"),
                message="not-part-of-contract",
            )

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "extra_forbidden")
        self.assertEqual(error["loc"], ("message",))

    def test_failure_response_success_field_is_always_false(self) -> None:
        response = FailureResponse(
            success=False,
            error=ErrorPayload(code="UNKNOWN_ERROR"),
        )

        self.assertIs(response.success, False)
        self.assertIs(response.model_dump(mode="json")["success"], False)

    def test_failure_response_rejects_true_success_value(self) -> None:
        with self.assertRaises(ValidationError) as context:
            FailureResponse(
                success=True,
                error=ErrorPayload(code="UNKNOWN_ERROR"),
            )

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "literal_error")
        self.assertEqual(error["loc"], ("success",))

    def test_error_payload_rejects_blank_error_code(self) -> None:
        with self.assertRaises(ValidationError) as context:
            ErrorPayload(code="")

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "string_too_short")
        self.assertEqual(error["loc"], ("code",))

    def test_error_payload_requires_error_code(self) -> None:
        with self.assertRaises(ValidationError) as context:
            ErrorPayload()

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "missing")
        self.assertEqual(error["loc"], ("code",))


if __name__ == "__main__":
    unittest.main()
