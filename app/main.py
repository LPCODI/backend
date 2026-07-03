"""FastAPI application entrypoint."""

from fastapi import APIRouter, FastAPI

from app.api.router import include_api_v1_router
from app.core import (
    Settings,
    build_openapi_metadata,
    configure_cors,
    configure_exception_handlers,
    get_settings,
)


def create_app(
    settings: Settings | None = None,
    api_v1_router: APIRouter | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application."""

    app_settings = settings or get_settings()
    app = FastAPI(
        debug=app_settings.debug,
        **build_openapi_metadata(app_settings),
    )
    app.state.settings = app_settings

    configure_exception_handlers(app)
    configure_cors(app, app_settings)
    if api_v1_router is None:
        include_api_v1_router(app, settings=app_settings)
    else:
        include_api_v1_router(app, router=api_v1_router, settings=app_settings)

    return app


app = create_app()
