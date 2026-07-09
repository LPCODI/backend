"""Presentation material file storage and persistence services."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import ApiError, Settings
from app.domain import ErrorCode, PresentationStatus
from app.models import PresentationFile, Slide, User
from app.services.document_parsing import (
    DocDocumentParserService,
    DocxDocumentParserService,
    PdfDocumentParserService,
    PptDocumentParserService,
    PptxDocumentParserService,
)
from app.services.interfaces import AnalysisInput, DocumentParserService
from app.services.presentations import (
    get_owned_presentation_project,
    validate_presentation_status_transition,
)

PRESENTATION_FILE_NOT_FOUND_MESSAGE = "발표 자료 파일을 찾을 수 없습니다."
PRESENTATION_FILE_TOO_LARGE_MESSAGE = "발표 자료 파일 크기가 허용 범위를 초과했습니다."
PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE = "지원하지 않는 발표 자료 파일 형식입니다."
PRESENTATION_FILE_STATUS_UPLOADED = "UPLOADED"
PRESENTATION_FILE_STATUS_PARSING = "PARSING"
PRESENTATION_FILE_STATUS_PARSED = "PARSED"
PRESENTATION_FILE_STATUS_FAILED = "FAILED"
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


@dataclass(frozen=True)
class PresentationParseSummary:
    """Persisted parse result summary returned by the parse API."""

    presentation_id: int
    file_id: int
    status: str
    slide_count: int
    parser_provider: str
    parser_version: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PresentationParseResult:
    """Latest persisted parse state and slides for one presentation."""

    presentation_file: PresentationFile
    slides: tuple[Slide, ...]


def get_document_parser_for_file_type(file_type: str) -> DocumentParserService:
    """Return a document parser adapter for a persisted presentation file type."""

    normalized_file_type = file_type.upper()
    if normalized_file_type == "PPT":
        return PptDocumentParserService()
    if normalized_file_type == "PPTX":
        return PptxDocumentParserService()
    if normalized_file_type == "PDF":
        return PdfDocumentParserService()
    if normalized_file_type == "DOC":
        return DocDocumentParserService()
    if normalized_file_type == "DOCX":
        return DocxDocumentParserService()
    raise ApiError(
        status_code=HTTPStatus.BAD_REQUEST,
        code=ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE,
        message=PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE,
        details={"fileType": file_type},
    )


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


def _next_sqlite_slide_id(db: Session) -> int | None:
    """Return a slide id for SQLite, whose BIGINT identity columns do not autoincrement."""

    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(Slide.slide_id), 0) + 1)).scalar_one()
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


def get_latest_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationFile:
    """Return the latest active material file for one owned presentation project."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = (
        select(PresentationFile)
        .where(
            PresentationFile.presentation_id == presentation.presentation_id,
            PresentationFile.deleted_at.is_(None),
        )
        .order_by(PresentationFile.uploaded_at.desc(), PresentationFile.file_id.desc())
    )
    presentation_file = db.execute(statement).scalars().first()
    if presentation_file is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.PRESENTATION_FILE_NOT_FOUND,
            message=PRESENTATION_FILE_NOT_FOUND_MESSAGE,
        )
    return presentation_file


def get_latest_uploaded_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationFile:
    """Return the latest active uploaded file for one owned presentation project."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = (
        select(PresentationFile)
        .where(
            PresentationFile.presentation_id == presentation.presentation_id,
            PresentationFile.deleted_at.is_(None),
            PresentationFile.status == PRESENTATION_FILE_STATUS_UPLOADED,
        )
        .order_by(PresentationFile.uploaded_at.desc(), PresentationFile.file_id.desc())
    )
    presentation_file = db.execute(statement).scalars().first()
    if presentation_file is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.PRESENTATION_FILE_NOT_FOUND,
            message=PRESENTATION_FILE_NOT_FOUND_MESSAGE,
        )
    return presentation_file


def get_presentation_parse_result(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationParseResult:
    """Return the latest file parse state and its persisted slides."""

    presentation_file = get_latest_presentation_file(db, user=user, presentation_id=presentation_id)
    slide_statement = (
        select(Slide)
        .where(
            Slide.presentation_id == presentation_id,
            Slide.file_id == presentation_file.file_id,
        )
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    slides = tuple(db.execute(slide_statement).scalars().all())
    return PresentationParseResult(presentation_file=presentation_file, slides=slides)


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


def _slide_text(parsed_slide: dict[str, object]) -> str | None:
    raw_text = parsed_slide.get("rawText")
    if isinstance(raw_text, str) and raw_text.strip():
        return raw_text
    text_parts = [
        value.strip()
        for key in ("title", "body")
        if isinstance((value := parsed_slide.get(key)), str) and value.strip()
    ]
    return "\n\n".join(text_parts) if text_parts else None


def _mark_parse_failed(
    db: Session,
    *,
    presentation_file: PresentationFile,
    message: str,
) -> None:
    presentation = presentation_file.presentation
    presentation_file.status = PRESENTATION_FILE_STATUS_FAILED
    presentation_file.parse_error_message = message
    if presentation.status != PresentationStatus.FAILED:
        try:
            validate_presentation_status_transition(
                current_status=presentation.status,
                next_status=PresentationStatus.FAILED,
            )
            presentation.status = PresentationStatus.FAILED
        except ApiError:
            pass
    db.commit()


async def parse_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    settings: Settings,
    file_id: int | None = None,
    parser: DocumentParserService | None = None,
) -> PresentationParseSummary:
    """Parse an uploaded material file and persist normalized slides."""

    presentation_file = (
        get_owned_presentation_file(
            db,
            user=user,
            presentation_id=presentation_id,
            file_id=file_id,
        )
        if file_id is not None
        else get_latest_uploaded_presentation_file(db, user=user, presentation_id=presentation_id)
    )
    presentation = presentation_file.presentation
    if presentation_file.status != PRESENTATION_FILE_STATUS_UPLOADED:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.PRESENTATION_INVALID_STATUS_TRANSITION,
            message="업로드 완료 상태의 발표 자료만 파싱할 수 있습니다.",
            details={
                "fileId": presentation_file.file_id,
                "currentFileStatus": presentation_file.status,
                "requiredFileStatus": PRESENTATION_FILE_STATUS_UPLOADED,
            },
        )

    validate_presentation_status_transition(
        current_status=presentation.status,
        next_status=PresentationStatus.PARSING,
    )
    presentation.status = PresentationStatus.PARSING
    presentation_file.status = PRESENTATION_FILE_STATUS_PARSING
    presentation_file.parse_error_message = None
    db.commit()

    parser_adapter = parser or get_document_parser_for_file_type(presentation_file.file_type)
    source_path = settings.local_storage_path / presentation_file.object_key
    try:
        parse_result = await parser_adapter.parse(
            AnalysisInput(
                resource_id=str(presentation_file.file_id),
                file_path=source_path,
                metadata={
                    "presentationId": presentation.presentation_id,
                    "fileId": presentation_file.file_id,
                    "fileType": presentation_file.file_type,
                    "originalFilename": presentation_file.original_filename,
                },
            )
        )
    except ApiError as exc:
        _mark_parse_failed(db, presentation_file=presentation_file, message=exc.message)
        raise
    except Exception as exc:
        _mark_parse_failed(db, presentation_file=presentation_file, message=str(exc))
        raise

    db.execute(delete(Slide).where(Slide.file_id == presentation_file.file_id))
    next_sqlite_slide_id = _next_sqlite_slide_id(db)
    for index, parsed_slide in enumerate(parse_result.slides, start=1):
        slide_number = int(parsed_slide.get("slideNumber") or index)
        sort_order = int(parsed_slide.get("sortOrder") or index)
        title = parsed_slide.get("title")
        notes = parsed_slide.get("notes")
        slide_kwargs: dict[str, object] = {
            "presentation_id": presentation.presentation_id,
            "file_id": presentation_file.file_id,
            "slide_number": slide_number,
            "sort_order": sort_order,
            "title": title if isinstance(title, str) else None,
            "raw_text": _slide_text(parsed_slide),
            "notes_text": notes if isinstance(notes, str) else None,
        }
        if next_sqlite_slide_id is not None:
            slide_kwargs["slide_id"] = next_sqlite_slide_id
            next_sqlite_slide_id += 1
        db.add(Slide(**slide_kwargs))

    validate_presentation_status_transition(
        current_status=presentation.status,
        next_status=PresentationStatus.PARSED,
    )
    presentation.status = PresentationStatus.PARSED
    presentation_file.status = PRESENTATION_FILE_STATUS_PARSED
    presentation_file.slide_count = len(parse_result.slides)
    presentation_file.parsed_at = datetime.now(timezone.utc)
    db.commit()

    return PresentationParseSummary(
        presentation_id=presentation.presentation_id,
        file_id=presentation_file.file_id,
        status=presentation_file.status,
        slide_count=presentation_file.slide_count or 0,
        parser_provider=parse_result.provider,
        parser_version=parse_result.version,
        warnings=parse_result.warnings,
    )


__all__ = [
    "ALLOWED_PRESENTATION_FILE_TYPES",
    "DEFAULT_MAX_PRESENTATION_FILE_SIZE_BYTES",
    "LOCAL_PRESENTATION_FILE_BUCKET",
    "LocalPresentationFileStorage",
    "PRESENTATION_FILE_NOT_FOUND_MESSAGE",
    "PRESENTATION_FILE_STATUS_FAILED",
    "PRESENTATION_FILE_STATUS_PARSED",
    "PRESENTATION_FILE_STATUS_PARSING",
    "PRESENTATION_FILE_STATUS_UPLOADED",
    "PRESENTATION_FILE_TOO_LARGE_MESSAGE",
    "PRESENTATION_FILE_UNSUPPORTED_TYPE_MESSAGE",
    "PresentationFileStorage",
    "PresentationParseResult",
    "PresentationParseSummary",
    "StoredPresentationFile",
    "create_presentation_file",
    "delete_presentation_file",
    "get_document_parser_for_file_type",
    "get_latest_presentation_file",
    "get_latest_uploaded_presentation_file",
    "get_owned_presentation_file",
    "get_presentation_parse_result",
    "get_presentation_file_storage",
    "list_presentation_files",
    "parse_presentation_file",
]
