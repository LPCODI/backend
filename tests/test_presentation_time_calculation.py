import unittest
from http import HTTPStatus

from app.core import ApiError
from app.domain import ErrorCode
from app.services.presentations import (
    MAX_TOTAL_DURATION_SECONDS,
    MIN_PRESENTATION_DURATION_SECONDS,
    MIN_TOTAL_DURATION_SECONDS,
    calculate_presentation_duration_seconds,
    validate_presentation_time_input,
)


class PresentationTimeCalculationTest(unittest.TestCase):
    def test_available_presentation_time_is_total_time_minus_qa_time(self) -> None:
        self.assertEqual(
            calculate_presentation_duration_seconds(
                total_duration_seconds=600,
                qa_duration_seconds=180,
            ),
            420,
        )

    def test_zero_qa_time_leaves_total_time_available_for_presentation(self) -> None:
        self.assertEqual(
            calculate_presentation_duration_seconds(
                total_duration_seconds=300,
                qa_duration_seconds=0,
            ),
            300,
        )

    def test_time_validation_accepts_specification_boundaries(self) -> None:
        minimum = validate_presentation_time_input(
            total_duration_seconds=MIN_TOTAL_DURATION_SECONDS,
            qa_duration_seconds=MIN_TOTAL_DURATION_SECONDS - MIN_PRESENTATION_DURATION_SECONDS,
        )
        maximum = validate_presentation_time_input(
            total_duration_seconds=MAX_TOTAL_DURATION_SECONDS,
            qa_duration_seconds=0,
        )

        self.assertEqual(minimum.presentation_duration_seconds, MIN_PRESENTATION_DURATION_SECONDS)
        self.assertEqual(maximum.presentation_duration_seconds, MAX_TOTAL_DURATION_SECONDS)

    def test_time_validation_rejects_total_time_shorter_than_two_minutes(self) -> None:
        self.assertInvalidTimeRange(
            total_duration_seconds=MIN_TOTAL_DURATION_SECONDS - 1,
            qa_duration_seconds=0,
            reason="total_duration_too_short",
        )

    def test_time_validation_rejects_total_time_longer_than_two_hours(self) -> None:
        self.assertInvalidTimeRange(
            total_duration_seconds=MAX_TOTAL_DURATION_SECONDS + 1,
            qa_duration_seconds=0,
            reason="total_duration_too_long",
        )

    def test_time_validation_rejects_negative_qa_time(self) -> None:
        self.assertInvalidTimeRange(
            total_duration_seconds=300,
            qa_duration_seconds=-1,
            reason="qa_duration_negative",
        )

    def test_time_validation_rejects_qa_time_equal_to_or_greater_than_total(self) -> None:
        self.assertInvalidTimeRange(
            total_duration_seconds=300,
            qa_duration_seconds=300,
            reason="qa_duration_not_less_than_total",
        )
        self.assertInvalidTimeRange(
            total_duration_seconds=300,
            qa_duration_seconds=301,
            reason="qa_duration_not_less_than_total",
        )

    def test_time_validation_rejects_available_presentation_time_under_one_minute(self) -> None:
        self.assertInvalidTimeRange(
            total_duration_seconds=300,
            qa_duration_seconds=241,
            reason="presentation_duration_too_short",
        )

    def assertInvalidTimeRange(
        self,
        *,
        total_duration_seconds: int,
        qa_duration_seconds: int,
        reason: str,
    ) -> None:
        with self.assertRaises(ApiError) as context:
            validate_presentation_time_input(
                total_duration_seconds=total_duration_seconds,
                qa_duration_seconds=qa_duration_seconds,
            )

        self.assertEqual(context.exception.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(context.exception.code, ErrorCode.PRESENTATION_INVALID_TIME_RANGE)
        self.assertEqual(context.exception.details["reason"], reason)


if __name__ == "__main__":
    unittest.main()
