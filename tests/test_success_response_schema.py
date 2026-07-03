import unittest
from datetime import UTC, datetime

from pydantic import ValidationError

from app.schemas import DEFAULT_SUCCESS_MESSAGE, SuccessResponse


class SuccessResponseSchemaTest(unittest.TestCase):
    def test_success_response_wraps_payload_data(self) -> None:
        response = SuccessResponse[dict[str, str]](data={"status": "ok"})

        self.assertTrue(response.success)
        self.assertEqual(response.data, {"status": "ok"})
        self.assertEqual(response.message, DEFAULT_SUCCESS_MESSAGE)
        self.assertIsInstance(response.timestamp, datetime)

    def test_success_response_is_json_serializable(self) -> None:
        response = SuccessResponse[dict[str, int]](data={"presentationId": 1})

        payload = response.model_dump(mode="json")

        self.assertEqual(
            set(payload),
            {"success", "data", "message", "timestamp"},
        )
        self.assertEqual(payload["data"], {"presentationId": 1})
        self.assertIsInstance(payload["timestamp"], str)

    def test_success_response_fields_are_fixed_in_contract_order(self) -> None:
        response = SuccessResponse[None](data=None)

        self.assertEqual(
            list(response.model_dump(mode="json")),
            ["success", "data", "message", "timestamp"],
        )
        self.assertEqual(
            list(SuccessResponse.model_fields),
            ["success", "data", "message", "timestamp"],
        )

    def test_success_response_rejects_extra_fields(self) -> None:
        with self.assertRaises(ValidationError) as context:
            SuccessResponse[dict[str, str]](
                data={"status": "ok"},
                request_id="not-part-of-contract",
            )

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "extra_forbidden")
        self.assertEqual(error["loc"], ("request_id",))

    def test_success_response_success_field_is_always_true(self) -> None:
        response = SuccessResponse[dict[str, str]](
            success=True,
            data={"status": "ok"},
        )

        self.assertIs(response.success, True)
        self.assertIs(response.model_dump(mode="json")["success"], True)

    def test_success_response_rejects_false_success_value(self) -> None:
        with self.assertRaises(ValidationError) as context:
            SuccessResponse[dict[str, str]](
                success=False,
                data={"status": "ok"},
            )

        error = context.exception.errors()[0]
        self.assertEqual(error["type"], "literal_error")
        self.assertEqual(error["loc"], ("success",))

    def test_success_response_timestamp_is_iso_8601_with_timezone(self) -> None:
        response = SuccessResponse[dict[str, str]](data={"status": "ok"})

        timestamp = response.model_dump(mode="json")["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp)

        self.assertIsInstance(timestamp, str)
        self.assertIsNotNone(parsed_timestamp.tzinfo)
        self.assertEqual(parsed_timestamp.utcoffset(), UTC.utcoffset(parsed_timestamp))
        self.assertEqual(parsed_timestamp, response.timestamp)


if __name__ == "__main__":
    unittest.main()
