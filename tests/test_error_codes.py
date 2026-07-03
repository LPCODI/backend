import unittest

from app.domain import ERROR_CODES_BY_DOMAIN, ErrorCode, ErrorDomain
from app.core import HTTP_EXCEPTION_ERROR_CODE, INTERNAL_SERVER_ERROR_CODE


class ErrorCodesTest(unittest.TestCase):
    def test_error_codes_are_unique_string_values(self) -> None:
        values = [code.value for code in ErrorCode]

        self.assertEqual(len(values), len(set(values)))
        self.assertIn("PRESENTATION_NOT_FOUND", values)
        self.assertIn("JOB_CANNOT_BE_CANCELLED", values)

    def test_domain_error_code_groups_cover_all_codes(self) -> None:
        grouped_codes = {
            code for codes in ERROR_CODES_BY_DOMAIN.values() for code in codes
        }

        self.assertEqual(set(ErrorDomain), set(ERROR_CODES_BY_DOMAIN))
        self.assertEqual(set(ErrorCode), grouped_codes)

    def test_key_domains_define_expected_error_codes(self) -> None:
        self.assertIn(
            ErrorCode.PRESENTATION_INVALID_TIME_RANGE,
            ERROR_CODES_BY_DOMAIN[ErrorDomain.PRESENTATION],
        )
        self.assertIn(
            ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE,
            ERROR_CODES_BY_DOMAIN[ErrorDomain.PRESENTATION_FILE],
        )
        self.assertIn(
            ErrorCode.AUTHENTICATION_REQUIRED,
            ERROR_CODES_BY_DOMAIN[ErrorDomain.AUTH],
        )

    def test_global_exception_handler_codes_use_canonical_error_codes(self) -> None:
        self.assertEqual(HTTP_EXCEPTION_ERROR_CODE, ErrorCode.HTTP_ERROR.value)
        self.assertEqual(
            INTERNAL_SERVER_ERROR_CODE,
            ErrorCode.INTERNAL_SERVER_ERROR.value,
        )


if __name__ == "__main__":
    unittest.main()
