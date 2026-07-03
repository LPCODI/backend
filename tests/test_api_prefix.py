import unittest

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.api.router import include_api_v1_router
from app.core import Settings


class ApiPrefixTest(unittest.TestCase):
    def test_api_v1_router_is_mounted_under_default_prefix(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.get("/prefix-probe")
        def prefix_probe() -> dict[str, str]:
            return {"status": "ok"}

        include_api_v1_router(app, router=router, settings=Settings(_env_file=None))

        client = TestClient(app)
        self.assertEqual(client.get("/api/v1/prefix-probe").status_code, 200)
        self.assertEqual(client.get("/prefix-probe").status_code, 404)

    def test_api_v1_router_uses_configured_prefix(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.get("/prefix-probe")
        def prefix_probe() -> dict[str, str]:
            return {"status": "ok"}

        include_api_v1_router(
            app,
            router=router,
            settings=Settings(api_v1_prefix="/custom/v1", _env_file=None),
        )

        client = TestClient(app)
        self.assertEqual(client.get("/custom/v1/prefix-probe").status_code, 200)
        self.assertEqual(client.get("/api/v1/prefix-probe").status_code, 404)


if __name__ == "__main__":
    unittest.main()
