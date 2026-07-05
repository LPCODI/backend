"""Presentation project domain services."""

from dataclasses import dataclass
from http import HTTPStatus

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import ApiError
from app.domain import ErrorCode
from app.models import Presentation, User

MIN_TOTAL_DURATION_SECONDS = 120
MAX_TOTAL_DURATION_SECONDS = 7_200
MIN_PRESENTATION_DURATION_SECONDS = 60
PRESENTATION_INVALID_TIME_RANGE_MESSAGE = "발표 시간 조건이 올바르지 않습니다."
PRESENTATION_NOT_FOUND_MESSAGE = "발표 프로젝트를 찾을 수 없습니다."


@dataclass(frozen=True)
class PresentationTimeValidationResult:
    """Validated presentation time inputs and derived speaking duration."""

    total_duration_seconds: int
    qa_duration_seconds: int
    presentation_duration_seconds: int


def _invalid_time_range_error(reason: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.BAD_REQUEST,
        code=ErrorCode.PRESENTATION_INVALID_TIME_RANGE,
        message=PRESENTATION_INVALID_TIME_RANGE_MESSAGE,
        details={
            "reason": reason,
            "minTotalDurationSeconds": MIN_TOTAL_DURATION_SECONDS,
            "maxTotalDurationSeconds": MAX_TOTAL_DURATION_SECONDS,
            "minPresentationDurationSeconds": MIN_PRESENTATION_DURATION_SECONDS,
        },
    )


def validate_presentation_time_input(
    *,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> PresentationTimeValidationResult:
    """Validate project time inputs from the API specification."""

    if total_duration_seconds < MIN_TOTAL_DURATION_SECONDS:
        raise _invalid_time_range_error("total_duration_too_short")
    if total_duration_seconds > MAX_TOTAL_DURATION_SECONDS:
        raise _invalid_time_range_error("total_duration_too_long")
    if qa_duration_seconds < 0:
        raise _invalid_time_range_error("qa_duration_negative")
    if qa_duration_seconds >= total_duration_seconds:
        raise _invalid_time_range_error("qa_duration_not_less_than_total")

    presentation_duration_seconds = total_duration_seconds - qa_duration_seconds
    if presentation_duration_seconds < MIN_PRESENTATION_DURATION_SECONDS:
        raise _invalid_time_range_error("presentation_duration_too_short")

    return PresentationTimeValidationResult(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
        presentation_duration_seconds=presentation_duration_seconds,
    )


def calculate_presentation_duration_seconds(
    *,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> int:
    """Calculate available speaking time after reserving Q&A time."""

    return validate_presentation_time_input(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
    ).presentation_duration_seconds


def _next_sqlite_presentation_id(db: Session) -> int | None:
    """Return a presentation id for SQLite, whose BIGINT identity columns do not autoincrement."""

    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(Presentation.presentation_id), 0) + 1)).scalar_one()
    return int(next_id)


def create_presentation_project(
    db: Session,
    *,
    user: User,
    title: str,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> Presentation:
    """Create a presentation project for the authenticated user."""

    time_result = validate_presentation_time_input(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
    )
    presentation_kwargs: dict[str, object] = {
        "user_id": user.user_id,
        "title": title.strip(),
        "total_duration_seconds": time_result.total_duration_seconds,
        "qa_duration_seconds": time_result.qa_duration_seconds,
        "presentation_duration_seconds": time_result.presentation_duration_seconds,
    }
    sqlite_presentation_id = _next_sqlite_presentation_id(db)
    if sqlite_presentation_id is not None:
        presentation_kwargs["presentation_id"] = sqlite_presentation_id

    presentation = Presentation(**presentation_kwargs)
    db.add(presentation)
    db.commit()
    db.refresh(presentation)
    return presentation


def list_presentation_projects(db: Session, *, user: User) -> list[Presentation]:
    """Return non-deleted presentation projects owned by the authenticated user."""

    statement = (
        select(Presentation)
        .where(
            Presentation.user_id == user.user_id,
            Presentation.deleted_at.is_(None),
        )
        .order_by(Presentation.created_at.desc(), Presentation.presentation_id.desc())
    )
    return list(db.execute(statement).scalars().all())


def get_presentation_project(db: Session, *, user: User, presentation_id: int) -> Presentation:
    """Return one non-deleted presentation project owned by the authenticated user."""

    statement = select(Presentation).where(
        Presentation.presentation_id == presentation_id,
        Presentation.user_id == user.user_id,
        Presentation.deleted_at.is_(None),
    )
    presentation = db.execute(statement).scalar_one_or_none()
    if presentation is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.PRESENTATION_NOT_FOUND,
            message=PRESENTATION_NOT_FOUND_MESSAGE,
        )
    return presentation


__all__ = [
    "MAX_TOTAL_DURATION_SECONDS",
    "MIN_PRESENTATION_DURATION_SECONDS",
    "MIN_TOTAL_DURATION_SECONDS",
    "PRESENTATION_INVALID_TIME_RANGE_MESSAGE",
    "PRESENTATION_NOT_FOUND_MESSAGE",
    "PresentationTimeValidationResult",
    "calculate_presentation_duration_seconds",
    "create_presentation_project",
    "get_presentation_project",
    "list_presentation_projects",
    "validate_presentation_time_input",
]
