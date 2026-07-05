"""Global exception handlers that emit the common failure response shape."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain import ErrorCode
from app.schemas import DEFAULT_ERROR_MESSAGE, ErrorPayload, FailureResponse

HTTP_EXCEPTION_ERROR_CODE = ErrorCode.HTTP_ERROR.value
INTERNAL_SERVER_ERROR_CODE = ErrorCode.INTERNAL_SERVER_ERROR.value
INTERNAL_SERVER_ERROR_MESSAGE = "서버 오류가 발생했습니다."
REQUEST_VALIDATION_ERROR_CODE = ErrorCode.VALIDATION_ERROR.value
REQUEST_VALIDATION_ERROR_MESSAGE = "요청 값이 올바르지 않습니다."


class ApiError(Exception):
    """Domain-aware API error rendered with the common failure response shape."""

    def __init__(
        self,
        *,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _failure_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    payload = FailureResponse(
        error=ErrorPayload(
            code=code,
            message=message,
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def api_error_handler(
    request: Request,
    exception: ApiError,
) -> JSONResponse:
    """Convert domain API errors into the common failure wrapper."""

    del request
    return _failure_response(
        status_code=exception.status_code,
        code=exception.code.value,
        message=exception.message,
        details=exception.details,
    )


def _http_exception_message(exception: StarletteHTTPException) -> str:
    if isinstance(exception.detail, str) and exception.detail:
        return exception.detail
    try:
        return HTTPStatus(exception.status_code).phrase
    except ValueError:
        return DEFAULT_ERROR_MESSAGE


async def http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    """Convert framework HTTP errors into the common failure wrapper."""

    del request
    details = None if isinstance(exception.detail, str) else exception.detail
    return _failure_response(
        status_code=exception.status_code,
        code=HTTP_EXCEPTION_ERROR_CODE,
        message=_http_exception_message(exception),
        details=details,
    )


async def unhandled_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Hide unhandled server exceptions behind the common failure wrapper."""

    del request, exception
    return _failure_response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code=INTERNAL_SERVER_ERROR_CODE,
        message=INTERNAL_SERVER_ERROR_MESSAGE,
    )


async def request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """Convert request validation errors into the common failure wrapper."""

    del request
    return _failure_response(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code=REQUEST_VALIDATION_ERROR_CODE,
        message=REQUEST_VALIDATION_ERROR_MESSAGE,
        details={"errors": jsonable_encoder(exception.errors())},
    )


def configure_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on a FastAPI application."""

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "ApiError",
    "HTTP_EXCEPTION_ERROR_CODE",
    "INTERNAL_SERVER_ERROR_CODE",
    "INTERNAL_SERVER_ERROR_MESSAGE",
    "REQUEST_VALIDATION_ERROR_CODE",
    "REQUEST_VALIDATION_ERROR_MESSAGE",
    "api_error_handler",
    "configure_exception_handlers",
    "http_exception_handler",
    "request_validation_exception_handler",
    "unhandled_exception_handler",
]
