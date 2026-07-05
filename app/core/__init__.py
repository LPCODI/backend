"""Application core package for settings, security, and infrastructure wiring."""

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.cors import configure_cors
from app.core.exceptions import (
    ApiError,
    HTTP_EXCEPTION_ERROR_CODE,
    INTERNAL_SERVER_ERROR_CODE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    REQUEST_VALIDATION_ERROR_CODE,
    REQUEST_VALIDATION_ERROR_MESSAGE,
    configure_exception_handlers,
)
from app.core.openapi import API_VERSION, OPENAPI_TAGS, build_openapi_metadata
from app.core.passwords import (
    PASSWORD_HASH_PREFIX,
    PASSWORD_HASH_ROUNDS,
    PASSWORD_HASH_SCHEME,
    PASSWORD_HASH_VERSION,
    hash_password,
    verify_password,
)
from app.core.refresh_tokens import (
    REFRESH_TOKEN_BYTES,
    REFRESH_TOKEN_HASH_LENGTH,
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.tokens import (
    ACCESS_TOKEN_TYPE,
    TOKEN_TYPE_CLAIM,
    AccessTokenError,
    AccessTokenPayload,
    create_access_token,
    decode_access_token,
)

__all__ = [
    "ACCESS_TOKEN_TYPE",
    "API_VERSION",
    "ApiError",
    "AccessTokenError",
    "AccessTokenPayload",
    "HTTP_EXCEPTION_ERROR_CODE",
    "AppEnvironment",
    "INTERNAL_SERVER_ERROR_CODE",
    "INTERNAL_SERVER_ERROR_MESSAGE",
    "OPENAPI_TAGS",
    "PASSWORD_HASH_PREFIX",
    "PASSWORD_HASH_ROUNDS",
    "PASSWORD_HASH_SCHEME",
    "PASSWORD_HASH_VERSION",
    "REFRESH_TOKEN_BYTES",
    "REFRESH_TOKEN_HASH_LENGTH",
    "REQUEST_VALIDATION_ERROR_CODE",
    "REQUEST_VALIDATION_ERROR_MESSAGE",
    "Settings",
    "TOKEN_TYPE_CLAIM",
    "build_openapi_metadata",
    "configure_cors",
    "configure_exception_handlers",
    "create_access_token",
    "decode_access_token",
    "get_settings",
    "generate_refresh_token",
    "hash_password",
    "hash_refresh_token",
    "verify_password",
]
