"""Version 1 API package."""

from app.api.v1.router_registry import build_api_v1_router

api_router = build_api_v1_router()

__all__ = [
    "api_router",
    "build_api_v1_router",
]
