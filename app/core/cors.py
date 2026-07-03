"""CORS middleware wiring."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings


def configure_cors(app: FastAPI, settings: Settings | None = None) -> None:
    """Attach CORS middleware using the configured frontend origins."""

    app_settings = settings or get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
