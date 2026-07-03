"""Automatic router discovery for API v1 route modules."""

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType

from fastapi import APIRouter

DEFAULT_ROUTERS_PACKAGE = "app.api.v1.routers"
ROUTER_ATTRIBUTE = "router"


def _load_package(package: str | ModuleType) -> ModuleType:
    if isinstance(package, str):
        return import_module(package)
    return package


def iter_router_module_names(package: str | ModuleType = DEFAULT_ROUTERS_PACKAGE) -> tuple[str, ...]:
    """Return public module names in a route package in deterministic order."""

    package_module = _load_package(package)
    package_paths = getattr(package_module, "__path__", None)
    if package_paths is None:
        raise TypeError(f"{package_module.__name__} is not a package")

    module_names = (
        f"{package_module.__name__}.{module_info.name}"
        for module_info in iter_modules(package_paths)
        if not module_info.ispkg and not module_info.name.startswith("_")
    )
    return tuple(sorted(module_names))


def get_module_router(module_name: str, attribute: str = ROUTER_ATTRIBUTE) -> APIRouter | None:
    """Import a module and return its FastAPI router if it exposes one."""

    module = import_module(module_name)
    router = getattr(module, attribute, None)
    if router is None:
        return None
    if not isinstance(router, APIRouter):
        raise TypeError(f"{module_name}.{attribute} must be an APIRouter instance")
    return router


def register_package_routers(
    api_router: APIRouter,
    package: str | ModuleType = DEFAULT_ROUTERS_PACKAGE,
) -> tuple[str, ...]:
    """Include every router exposed by public modules in the given package."""

    registered_modules: list[str] = []
    for module_name in iter_router_module_names(package):
        module_router = get_module_router(module_name)
        if module_router is None:
            continue
        api_router.include_router(module_router)
        registered_modules.append(module_name)
    return tuple(registered_modules)


def build_api_v1_router(package: str | ModuleType = DEFAULT_ROUTERS_PACKAGE) -> APIRouter:
    """Create the API v1 router and attach discovered route module routers."""

    api_router = APIRouter()
    register_package_routers(api_router, package=package)
    return api_router


__all__ = [
    "DEFAULT_ROUTERS_PACKAGE",
    "ROUTER_ATTRIBUTE",
    "build_api_v1_router",
    "get_module_router",
    "iter_router_module_names",
    "register_package_routers",
]
