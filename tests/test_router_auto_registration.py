import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router_registry import (
    build_api_v1_router,
    iter_router_module_names,
    register_package_routers,
)


class RouterAutoRegistrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.package_root = Path(self.temp_dir.name) / "auto_router_fixture"
        self.package_root.mkdir()
        (self.package_root / "__init__.py").write_text("", encoding="utf-8")
        sys.path.insert(0, self.temp_dir.name)

    def tearDown(self) -> None:
        sys.path.remove(self.temp_dir.name)
        for module_name in list(sys.modules):
            if module_name == "auto_router_fixture" or module_name.startswith(
                "auto_router_fixture."
            ):
                sys.modules.pop(module_name, None)
        self.temp_dir.cleanup()

    def write_module(self, name: str, source: str) -> None:
        (self.package_root / f"{name}.py").write_text(
            textwrap.dedent(source),
            encoding="utf-8",
        )
        importlib.invalidate_caches()

    def test_iter_router_module_names_returns_public_modules_in_order(self) -> None:
        self.write_module("beta", "router = None")
        self.write_module("_private", "router = None")
        self.write_module("alpha", "router = None")

        self.assertEqual(
            iter_router_module_names("auto_router_fixture"),
            ("auto_router_fixture.alpha", "auto_router_fixture.beta"),
        )

    def test_build_api_v1_router_includes_discovered_module_routers(self) -> None:
        self.write_module(
            "alpha",
            """
            from fastapi import APIRouter

            router = APIRouter(prefix="/alpha", tags=["alpha"])

            @router.get("")
            def read_alpha() -> dict[str, str]:
                return {"route": "alpha"}
            """,
        )
        self.write_module(
            "beta",
            """
            from fastapi import APIRouter

            router = APIRouter(prefix="/beta", tags=["beta"])

            @router.get("")
            def read_beta() -> dict[str, str]:
                return {"route": "beta"}
            """,
        )
        self.write_module("no_router", "VALUE = 'ignored'")

        app = FastAPI()
        app.include_router(build_api_v1_router(package="auto_router_fixture"), prefix="/api/v1")
        client = TestClient(app)

        self.assertEqual(client.get("/api/v1/alpha").json(), {"route": "alpha"})
        self.assertEqual(client.get("/api/v1/beta").json(), {"route": "beta"})
        self.assertEqual(client.get("/api/v1/no-router").status_code, 404)

    def test_register_package_routers_returns_registered_module_names(self) -> None:
        self.write_module(
            "alpha",
            """
            from fastapi import APIRouter

            router = APIRouter()
            """,
        )
        self.write_module("no_router", "VALUE = 'ignored'")

        api_router = APIRouter()

        self.assertEqual(
            register_package_routers(api_router, package="auto_router_fixture"),
            ("auto_router_fixture.alpha",),
        )

    def test_invalid_router_attribute_fails_fast(self) -> None:
        self.write_module("invalid", "router = object()")

        with self.assertRaisesRegex(TypeError, "must be an APIRouter"):
            build_api_v1_router(package="auto_router_fixture")


if __name__ == "__main__":
    unittest.main()
