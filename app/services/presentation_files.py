"""Presentation material file storage and persistence services."""

from dataclasses import dataclass
from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import ApiError, Settings
from app.domain import ErrorCode, PresentationStatus
from app.models import PresentationFile, User
from app.services.presentations import (
    get_owned_presentation_project,
    validate_presentation_status_transition,
)

PRESENTATION_FILE_NOT_FOUND_MESSAGE = "발표 자료 파일을 찾을 수 없습니다."
PRESENTATION_FILE_TOO_LARGE_MESSAGE = "발표 자료 파일 크기가 허용 범위를 초과했습니다."
PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE = "지원하지 않는 발표 자료 파일 형식입니다."
PRESENTATION_FILE_STATUS_UPLOADED = "UPLOADED"
LOCAL_PRESENTATION_FILE_BUCKET = "local-presentation-files"
DEFAULT_MAX_PRESENTATION_FILE_SIZE_BYTES = 50 * 1024 * 1024

ALLOWED_PRESENTATION_FILE_TYPES: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".ppt": frozenset(
        {
            "application/vnd.ms-powerpoint",
            "application/octet-stream",
        }
    ),
    ".pptx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/octet-stream",
        }
    ),
    ".doc": frozenset(
        {
            "application/msword",
            "application/octet-stream",
        }
    ),
    ".docx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        }
    ),
}


@dataclass(frozen=True)
class StoredPresentationFile:
    """Metadata returned by a file storage backend after bytes are written."""

    storage_bucket: str
    object_key: str
    stored_filename: str
    checksum: str
    file_size_bytes: int


class PresentationFileStorage:
    """Storage interface for uploaded presentation material files."""

    def save(
        self,
        *,
        user_id: int,
        presentation_id: int,
        original_filename: str,
        content: bytes,
    ) -> StoredPresentationFile:
        raise NotImplementedError

    def delete(self, *, object_key: str) -> None:
        raise NotImplementedError


class LocalPresentationFileStorage(PresentationFileStorage):
    """Development storage backend that writes files below the configured local path."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path

    def save(
        self,
        *,
        user_id: int,
        presentation_id: int,
        original_filename: str,
        content: bytes,
    ) -> StoredPresentationFile:
        safe_name = Path(original_filename).name or "presentation-file"
        suffix = Path(safe_name).suffix.lower()
        stored_filename = f"{uuid4().hex}{suffix}"
        object_key = f"presentations/{user_id}/{presentation_id}/{stored_filename}"
        destination = self.root_path / object_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredPresentationFile(
            storage_bucket=LOCAL_PRESENTATION_FILE_BUCKET,
            object_key=object_key,
            stored_filename=stored_filename,
            checksum=sha256(content).hexdigest(),
            file_size_bytes=len(content),
        )

    def delete(self, *, object_key: str) -> None:
        target = self.root_path / object_key
        try:
            target.unlink()
        except FileNotFoundError:
            return


def get_presentation_file_storage(settings: Settings) -> PresentationFileStorage:
    """Return the configured storage backend for presentation files."""

    if settings.storage_backend != "local":
        raise ApiError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code=ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="설정된 파일 저장소를 사용할 수 없습니다.",
            details={"storageBackend": settings.storage_backend},
        )
    return LocalPresentationFileStorage(settings.local_storage_path)


def _next_sqlite_presentation_file_id(db: Session) -> int | None:
    """Return a file id for SQLite, whose BIGINT identity columns do not autoincrement."""

    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(PresentationFile.file_id), 0) + 1)).scalar_one()
    return int(next_id)


def _validate_presentation_file(
    *,
    filename: str,
    content_type: str | None,
    file_size_bytes: int,
    max_file_size_bytes: int,
) -> str:
    extension = Path(filename).suffix.lower()
    allowed_mime_types = ALLOWED_PRESENTATION_FILE_TYPES.get(extension)
    if allowed_mime_types is None:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE,
            message=PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE,
            details={"allowedExtensions": sorted(ALLOWED_PRESENTATION_FILE_TYPES)},
        )

    if content_type not in allowed_mime_types:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE,
            message=PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE,
            details={
                "contentType": content_type,
                "allowedContentTypes": sorted(allowed_mime_types),
            },
        )

    if file_size_bytes > max_file_size_bytes:
        raise ApiError(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            code=ErrorCode.PRESENTATION_FILE_TOO_LARGE,
            message=PRESENTATION_FILE_TOO_LARGE_MESSAGE,
            details={
                "fileSizeBytes": file_size_bytes,
                "maxFileSizeBytes": max_file_size_bytes,
            },
        )

    return extension.removeprefix(".").upper()


def create_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    filename: str,
    content_type: str | None,
    content: bytes,
    settings: Settings,
    storage: PresentationFileStorage | None = None,
) -> PresentationFile:
    """Validate, store, and persist an uploaded presentation material file."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    file_type = _validate_presentation_file(
        filename=filename,
        content_type=content_type,
        file_size_bytes=len(content),
        max_file_size_bytes=settings.max_presentation_file_size_bytes,
    )
    storage_backend = storage or get_presentation_file_storage(settings)
    stored = storage_backend.save(
        user_id=user.user_id,
        presentation_id=presentation.presentation_id,
        original_filename=filename,
        content=content,
    )
    file_kwargs: dict[str, object] = {
        "presentation_id": presentation.presentation_id,
        "original_filename": Path(filename).name,
        "stored_filename": stored.stored_filename,
        "file_type": file_type,
        "mime_type": content_type or "",
        "file_size_bytes": stored.file_size_bytes,
        "storage_bucket": stored.storage_bucket,
        "object_key": stored.object_key,
        "checksum": stored.checksum,
        "status": PRESENTATION_FILE_STATUS_UPLOADED,
    }
    sqlite_file_id = _next_sqlite_presentation_file_id(db)
    if sqlite_file_id is not None:
        file_kwargs["file_id"] = sqlite_file_id

    presentation_file = PresentationFile(**file_kwargs)
    if presentation.status == PresentationStatus.DRAFT:
        validate_presentation_status_transition(
            current_status=presentation.status,
            next_status=PresentationStatus.FILE_UPLOADED,
        )
        presentation.status = PresentationStatus.FILE_UPLOADED

    db.add(presentation_file)
    db.commit()
    db.refresh(presentation_file)
    return presentation_file


def list_presentation_files(db: Session, *, user: User, presentation_id: int) -> list[PresentationFile]:
    """Return active uploaded files for one owned presentation project."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = (
        select(PresentationFile)
        .where(
            PresentationFile.presentation_id == presentation.presentation_id,
            PresentationFile.deleted_at.is_(None),
        )
        .order_by(PresentationFile.uploaded_at.desc(), PresentationFile.file_id.desc())
    )
    return list(db.execute(statement).scalars().all())


def get_owned_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    file_id: int,
) -> PresentationFile:
    """Return one active file after presentation ownership verification."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = select(PresentationFile).where(
        PresentationFile.file_id == file_id,
        PresentationFile.presentation_id == presentation.presentation_id,
        PresentationFile.deleted_at.is_(None),
    )
    presentation_file = db.execute(statement).scalar_one_or_none()
    if presentation_file is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.PRESENTATION_FILE_NOT_FOUND,
            message=PRESENTATION_FILE_NOT_FOUND_MESSAGE,
        )
    return presentation_file


def delete_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    file_id: int,
    settings: Settings,
    storage: PresentationFileStorage | None = None,
) -> None:
    """Soft-delete one uploaded file and remove its local object when possible."""

    presentation_file = get_owned_presentation_file(
        db,
        user=user,
        presentation_id=presentation_id,
        file_id=file_id,
    )
    storage_backend = storage or get_presentation_file_storage(settings)
    storage_backend.delete(object_key=presentation_file.object_key)
    presentation_file.soft_delete()
    db.commit()


__all__ = [
    "ALLOWED_PRESENTATION_FILE_TYPES",
    "DEFAULT_MAX_PRESENTATION_FILE_SIZE_BYTES",
    "LOCAL_PRESENTATION_FILE_BUCKET",
    "LocalPresentationFileStorage",
    "PRESENTATION_FILE_NOT_FOUND_MESSAGE",
    "PRESENTATION_FILE_STATUS_UPLOADED",
    "PRESENTATION_FILE_TOO_LARGE_MESSAGE",
    "PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE",
    "PresentationFileStorage",
    "StoredPresentationFile",
    "create_presentation_file",
    "delete_presentation_file",
    "get_owned_presentation_file",
    "get_presentation_file_storage",
    "list_presentation_files",
]
