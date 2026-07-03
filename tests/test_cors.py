import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import Settings, configure_cors


class CorsTest(unittest.TestCase):
    def test_configured_origin_receives_cors_headers(self) -> None:
        app = FastAPI()
        configure_cors(
            app,
            settings=Settings(cors_origins=("http://localhost:8081",), _env_file=None),
        )

        @app.get("/cors-probe")
        def cors_probe() -> dict[str, str]:
            return {"status": "ok"}

        response = TestClient(app).get(
            "/cors-probe",
            headers={"Origin": "http://localhost:8081"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:8081",
        )
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

    def test_preflight_request_allows_configured_origin_and_method(self) -> None:
        app = FastAPI()
        configure_cors(
            app,
            settings=Settings(cors_origins=("http://localhost:3000",), _env_file=None),
        )

        response = TestClient(app).options(
            "/cors-probe",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_unconfigured_origin_does_not_receive_allow_origin_header(self) -> None:
        app = FastAPI()
        configure_cors(
            app,
            settings=Settings(cors_origins=("http://localhost:3000",), _env_file=None),
        )

        @app.get("/cors-probe")
        def cors_probe() -> dict[str, str]:
            return {"status": "ok"}

        response = TestClient(app).get(
            "/cors-probe",
            headers={"Origin": "http://malicious.example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
