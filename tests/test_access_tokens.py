import unittest
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core import (
    ACCESS_TOKEN_TYPE,
    TOKEN_TYPE_CLAIM,
    AccessTokenError,
    AccessTokenPayload,
    Settings,
    create_access_token,
    decode_access_token,
)
from app.domain import ErrorCode


class AccessTokenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            jwt_secret_key="test-access-secret",
            access_token_expire_minutes=15,
            _env_file=None,
        )
        self.issued_at = datetime.now(UTC).replace(microsecond=0)

    def test_create_access_token_encodes_user_subject_and_lifetime(self) -> None:
        token = create_access_token(
            user_id=42,
            settings=self.settings,
            issued_at=self.issued_at,
        )

        claims = jwt.decode(
            token,
            self.settings.jwt_secret_key.get_secret_value(),
            algorithms=[self.settings.jwt_algorithm],
        )

        self.assertEqual(claims["sub"], "42")
        self.assertEqual(claims[TOKEN_TYPE_CLAIM], ACCESS_TOKEN_TYPE)
        self.assertEqual(claims["iat"], int(self.issued_at.timestamp()))
        self.assertEqual(
            claims["exp"],
            int((self.issued_at + timedelta(minutes=15)).timestamp()),
        )

    def test_decode_access_token_returns_validated_payload(self) -> None:
        token = create_access_token(
            user_id=7,
            settings=self.settings,
            issued_at=self.issued_at,
        )

        payload = decode_access_token(token, settings=self.settings)

        self.assertIsInstance(payload, AccessTokenPayload)
        self.assertEqual(payload.user_id, 7)
        self.assertEqual(payload.issued_at, self.issued_at)
        self.assertEqual(payload.expires_at, self.issued_at + timedelta(minutes=15))

    def test_create_access_token_rejects_invalid_user_id(self) -> None:
        with self.assertRaises(ValueError):
            create_access_token(user_id=0, settings=self.settings)

    def test_decode_access_token_rejects_expired_token(self) -> None:
        token = create_access_token(
            user_id=3,
            settings=self.settings,
            issued_at=self.issued_at,
            expires_delta=timedelta(seconds=-1),
        )

        with self.assertRaises(AccessTokenError) as context:
            decode_access_token(token, settings=self.settings)

        self.assertEqual(context.exception.code, ErrorCode.TOKEN_EXPIRED)

    def test_decode_access_token_rejects_wrong_signature(self) -> None:
        token = create_access_token(
            user_id=3,
            settings=self.settings,
            issued_at=self.issued_at,
        )
        other_settings = Settings(jwt_secret_key="other-secret", _env_file=None)

        with self.assertRaises(AccessTokenError) as context:
            decode_access_token(token, settings=other_settings)

        self.assertEqual(context.exception.code, ErrorCode.TOKEN_INVALID)

    def test_decode_access_token_rejects_non_access_token_type(self) -> None:
        claims = {
            "sub": "7",
            TOKEN_TYPE_CLAIM: "refresh",
            "iat": int(self.issued_at.timestamp()),
            "exp": int((self.issued_at + timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(
            claims,
            self.settings.jwt_secret_key.get_secret_value(),
            algorithm=self.settings.jwt_algorithm,
        )

        with self.assertRaises(AccessTokenError) as context:
            decode_access_token(token, settings=self.settings)

        self.assertEqual(context.exception.code, ErrorCode.TOKEN_INVALID)

    def test_decode_access_token_rejects_invalid_subject(self) -> None:
        claims = {
            "sub": "not-a-user-id",
            TOKEN_TYPE_CLAIM: ACCESS_TOKEN_TYPE,
            "iat": int(self.issued_at.timestamp()),
            "exp": int((self.issued_at + timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(
            claims,
            self.settings.jwt_secret_key.get_secret_value(),
            algorithm=self.settings.jwt_algorithm,
        )

        with self.assertRaises(AccessTokenError) as context:
            decode_access_token(token, settings=self.settings)

        self.assertEqual(context.exception.code, ErrorCode.TOKEN_INVALID)


if __name__ == "__main__":
    unittest.main()
