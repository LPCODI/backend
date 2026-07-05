import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core import (
    REFRESH_TOKEN_HASH_LENGTH,
    Settings,
    decode_access_token,
    hash_refresh_token,
)
from app.db import Base
from app.domain import ErrorCode
from app.models import RefreshToken, User
from app.services import RefreshTokenError, RefreshTokenService, TokenPair


class RefreshTokenServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[User.__table__, RefreshToken.__table__])
        self.settings = Settings(
            jwt_secret_key="test-refresh-secret",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
            _env_file=None,
        )
        self.now = datetime.now(UTC).replace(microsecond=0)

    def _create_user(self, session: Session) -> User:
        user = User(
            user_id=1,
            email="student@example.com",
            password_hash="hash",
            name="Student",
        )
        session.add(user)
        session.flush()
        return user

    def _create_refresh_token(
        self,
        session: Session,
        *,
        raw_token: str = "valid-refresh-token",
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> RefreshToken:
        self._create_user(session)
        record = RefreshToken(
            refresh_token_id=1,
            user_id=1,
            token_hash=hash_refresh_token(raw_token),
            expires_at=expires_at or self.now + timedelta(days=14),
            revoked_at=revoked_at,
        )
        session.add(record)
        session.flush()
        return record

    def test_hash_refresh_token_is_stable_and_does_not_store_plaintext(self) -> None:
        token_hash = hash_refresh_token("raw-refresh-token")

        self.assertEqual(token_hash, hash_refresh_token("raw-refresh-token"))
        self.assertNotEqual(token_hash, "raw-refresh-token")
        self.assertEqual(len(token_hash), REFRESH_TOKEN_HASH_LENGTH)

    def test_issue_refresh_token_stores_hash_and_expiry(self) -> None:
        with Session(self.engine) as session:
            self._create_user(session)
            service = RefreshTokenService(session, self.settings)

            issue = service.issue_refresh_token(user_id=1, issued_at=self.now)

            self.assertIn(issue.record, session.new)
            self.assertNotEqual(issue.record.token_hash, issue.raw_token)
            self.assertEqual(issue.record.token_hash, hash_refresh_token(issue.raw_token))
            self.assertEqual(issue.record.expires_at, self.now + timedelta(days=14))
            self.assertIsNone(issue.record.revoked_at)

    def test_get_active_refresh_token_rejects_unknown_revoked_and_expired_tokens(self) -> None:
        with Session(self.engine) as session:
            service = RefreshTokenService(session, self.settings)

            with self.assertRaises(RefreshTokenError) as unknown:
                service.get_active_refresh_token("missing-token", now=self.now)

            self.assertEqual(unknown.exception.code, ErrorCode.TOKEN_INVALID)

        with Session(self.engine) as session:
            self._create_refresh_token(
                session,
                raw_token="revoked-token",
                revoked_at=self.now - timedelta(minutes=1),
            )
            service = RefreshTokenService(session, self.settings)

            with self.assertRaises(RefreshTokenError) as revoked:
                service.get_active_refresh_token("revoked-token", now=self.now)

            self.assertEqual(revoked.exception.code, ErrorCode.TOKEN_INVALID)

        with Session(self.engine) as session:
            self._create_refresh_token(
                session,
                raw_token="expired-token",
                expires_at=self.now - timedelta(seconds=1),
            )
            service = RefreshTokenService(session, self.settings)

            with self.assertRaises(RefreshTokenError) as expired:
                service.get_active_refresh_token("expired-token", now=self.now)

            self.assertEqual(expired.exception.code, ErrorCode.TOKEN_EXPIRED)

    def test_revoke_refresh_token_marks_matching_record_revoked(self) -> None:
        with Session(self.engine) as session:
            record = self._create_refresh_token(session)
            service = RefreshTokenService(session, self.settings)

            revoked = service.revoke_refresh_token("valid-refresh-token", revoked_at=self.now)

            self.assertIs(revoked, record)
            self.assertEqual(record.revoked_at, self.now)

    def test_rotate_refresh_token_revokes_old_record_and_adds_replacement(self) -> None:
        with Session(self.engine) as session:
            old_record = self._create_refresh_token(session)
            service = RefreshTokenService(session, self.settings)

            rotation = service.rotate_refresh_token("valid-refresh-token", rotated_at=self.now)

            self.assertIs(rotation.old_record, old_record)
            self.assertEqual(old_record.revoked_at, self.now)
            self.assertIn(rotation.issue.record, session.new)
            self.assertEqual(rotation.issue.record.user_id, old_record.user_id)
            self.assertNotEqual(rotation.issue.record.token_hash, old_record.token_hash)

    def test_refresh_token_pair_rotates_refresh_token_and_issues_access_token(self) -> None:
        with Session(self.engine) as session:
            old_record = self._create_refresh_token(session)
            service = RefreshTokenService(session, self.settings)

            token_pair = service.refresh_token_pair("valid-refresh-token", issued_at=self.now)

            self.assertIsInstance(token_pair, TokenPair)
            self.assertEqual(old_record.revoked_at, self.now)
            self.assertEqual(token_pair.access_token_expires_at, self.now + timedelta(minutes=30))
            self.assertEqual(token_pair.refresh_token_expires_at, self.now + timedelta(days=14))
            self.assertNotEqual(token_pair.refresh_token, "valid-refresh-token")

            payload = decode_access_token(token_pair.access_token, settings=self.settings)
            self.assertEqual(payload.user_id, 1)
            self.assertEqual(payload.issued_at, self.now)

    def test_revoke_user_refresh_tokens_revokes_only_active_user_tokens(self) -> None:
        with Session(self.engine) as session:
            self._create_user(session)
            active = RefreshToken(
                refresh_token_id=1,
                user_id=1,
                token_hash=hash_refresh_token("active"),
                expires_at=self.now + timedelta(days=14),
            )
            already_revoked = RefreshToken(
                refresh_token_id=2,
                user_id=1,
                token_hash=hash_refresh_token("revoked"),
                expires_at=self.now + timedelta(days=14),
                revoked_at=self.now - timedelta(days=1),
            )
            session.add_all([active, already_revoked])
            session.flush()
            service = RefreshTokenService(session, self.settings)

            revoked_count = service.revoke_user_refresh_tokens(user_id=1, revoked_at=self.now)

            self.assertEqual(revoked_count, 1)
            self.assertEqual(active.revoked_at, self.now)
            self.assertEqual(already_revoked.revoked_at, self.now - timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
