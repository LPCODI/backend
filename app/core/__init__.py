"""Application core package for settings, security, and infrastructure wiring."""

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.cors import configure_cors
from app.core.exceptions import (
    HTTP_EXCEPTION_ERROR_CODE,
    INTERNAL_SERVER_ERROR_CODE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    REQUEST_VALIDATION_ERROR_CODE,
    REQUEST_VALIDATION_ERROR_MESSAGE,
    configure_exception_handlers,
)
from app.core.openapi import API_VERSION, OPENAPI_TAGS, build_openapi_metadata

__all__ = [
    "API_VERSION",
    "HTTP_EXCEPTION_ERROR_CODE",
    "AppEnvironment",
    "INTERNAL_SERVER_ERROR_CODE",
    "INTERNAL_SERVER_ERROR_MESSAGE",
    "OPENAPI_TAGS",
    "REQUEST_VALIDATION_ERROR_CODE",
    "REQUEST_VALIDATION_ERROR_MESSAGE",
    "Settings",
    "build_openapi_metadata",
    "configure_cors",
    "configure_exception_handlers",
    "get_settings",
]
