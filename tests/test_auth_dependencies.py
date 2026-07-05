import unittest
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import CurrentUser
from app.core import Settings, create_access_token
from app.db import Base, get_db
from app.domain import ErrorCode, UserStatus
from app.main import create_app
from app.models import User


class AuthDependenciesTest(unittest.TestCase):
    def setUp(self) -> None:
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
        Base.metadata.create_all(self.engine, tables=[User.__table__])
        self.settings = Settings(
            jwt_secret_key="test-current-user-secret",
            access_token_expire_minutes=30,
            _env_file=None,
        )

        router = APIRouter()

        @router.get("/auth/current-user-probe")
        def current_user_probe(current_user: CurrentUser) -> dict[str, object]:
            return {
                "user_id": current_user.user_id,
                "email": current_user.email,
                "name": current_user.name,
            }

        self.app = create_app(settings=self.settings, api_v1_router=router)
        self.app.dependency_overrides[get_db] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _override_db(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def _create_user(
        self,
        *,
        user_id: int = 1,
        status: UserStatus = UserStatus.ACTIVE,
        deleted: bool = False,
    ) -> User:
        with self.session_factory() as session:
            user = User(
                user_id=user_id,
                email=f"user{user_id}@example.com",
                password_hash="hash",
                name="Presenter",
                status=status,
                deleted_at=datetime(2026, 7, 4, 9, 0, 0, tzinfo=UTC) if deleted else None,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def _access_token(
        self,
        *,
        user_id: int = 1,
        issued_at: datetime | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        return create_access_token(
            user_id=user_id,
            settings=self.settings,
            issued_at=issued_at or datetime.now(UTC),
            expires_delta=expires_delta,
        )

    def _get_with_token(self, token: str | None) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
        response = self.client.get("/api/v1/auth/current-user-probe", headers=headers)
        return {"status_code": response.status_code, "payload": response.json()}

    def test_current_user_dependency_resolves_active_user_from_bearer_token(self) -> None:
        user = self._create_user()
        result = self._get_with_token(self._access_token(user_id=user.user_id))

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(
            result["payload"],
            {"user_id": 1, "email": "user1@example.com", "name": "Presenter"},
        )

    def test_current_user_dependency_requires_bearer_token(self) -> None:
        result = self._get_with_token(None)
        payload = result["payload"]

        self.assertEqual(result["status_code"], 401)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], ErrorCode.AUTHENTICATION_REQUIRED.value)

    def test_current_user_dependency_rejects_invalid_and_expired_tokens(self) -> None:
        invalid = self._get_with_token("not-a-jwt")
        expired_token = self._access_token(
            issued_at=datetime.now(UTC) - timedelta(hours=1),
            expires_delta=timedelta(minutes=1),
        )
        expired = self._get_with_token(expired_token)

        self.assertEqual(invalid["status_code"], 401)
        self.assertEqual(invalid["payload"]["error"]["code"], ErrorCode.TOKEN_INVALID.value)
        self.assertEqual(expired["status_code"], 401)
        self.assertEqual(expired["payload"]["error"]["code"], ErrorCode.TOKEN_EXPIRED.value)

    def test_current_user_dependency_rejects_missing_deleted_and_inactive_users(self) -> None:
        missing = self._get_with_token(self._access_token(user_id=99))
        self._create_user(user_id=2, deleted=True)
        deleted = self._get_with_token(self._access_token(user_id=2))
        self._create_user(user_id=3, status=UserStatus.SUSPENDED)
        inactive = self._get_with_token(self._access_token(user_id=3))

        self.assertEqual(missing["status_code"], 401)
        self.assertEqual(missing["payload"]["error"]["code"], ErrorCode.USER_NOT_FOUND.value)
        self.assertEqual(deleted["status_code"], 401)
        self.assertEqual(deleted["payload"]["error"]["code"], ErrorCode.USER_NOT_FOUND.value)
        self.assertEqual(inactive["status_code"], 403)
        self.assertEqual(inactive["payload"]["error"]["code"], ErrorCode.PERMISSION_DENIED.value)


if __name__ == "__main__":
    unittest.main()
