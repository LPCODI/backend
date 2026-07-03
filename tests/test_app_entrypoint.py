import unittest

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core import API_VERSION, Settings
from app.main import app, create_app


class AppEntrypointTest(unittest.TestCase):
    def test_create_app_applies_openapi_metadata(self) -> None:
        test_app = create_app(settings=Settings(app_name="Entrypoint Probe", _env_file=None))

        schema = TestClient(test_app).get("/openapi.json").json()

        self.assertEqual(schema["info"]["title"], "Entrypoint Probe")
        self.assertEqual(schema["info"]["version"], API_VERSION)

    def test_create_app_mounts_api_v1_router_under_configured_prefix(self) -> None:
        router = APIRouter()

        @router.get("/entrypoint-probe")
        def entrypoint_probe() -> dict[str, str]:
            return {"status": "ok"}

        test_app = create_app(
            settings=Settings(api_v1_prefix="/api/v1", _env_file=None),
            api_v1_router=router,
        )
        client = TestClient(test_app)

        self.assertEqual(client.get("/api/v1/entrypoint-probe").status_code, 200)
        self.assertEqual(client.get("/entrypoint-probe").status_code, 404)

    def test_create_app_applies_cors_middleware(self) -> None:
        test_app = create_app(
            settings=Settings(cors_origins=("http://localhost:8081",), _env_file=None),
        )

        response = TestClient(test_app).options(
            "/api/v1/entrypoint-probe",
            headers={
                "Origin": "http://localhost:8081",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:8081",
        )

    def test_module_level_app_is_fastapi_instance(self) -> None:
        self.assertEqual(app.title, "AI Speech Backend")
        self.assertEqual(app.version, API_VERSION)


if __name__ == "__main__":
    unittest.main()
