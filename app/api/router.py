"""Top-level API router wiring."""

from fastapi import APIRouter, FastAPI

from app.api.v1 import api_router as default_api_v1_router
from app.core import Settings, get_settings


def include_api_v1_router(
    app: FastAPI,
    router: APIRouter = default_api_v1_router,
    settings: Settings | None = None,
) -> None:
    """Mount the version 1 API router under the configured prefix."""

    app_settings = settings or get_settings()
    app.include_router(router, prefix=app_settings.api_v1_prefix)
