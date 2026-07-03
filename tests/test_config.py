import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings, get_settings


class SettingsTest(unittest.TestCase):
    def test_defaults_match_local_development_environment(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.app_name, "AI Speech Backend")
        self.assertEqual(settings.environment, AppEnvironment.LOCAL)
        self.assertEqual(settings.api_v1_prefix, "/api/v1")
        self.assertTrue(settings.database_url.startswith("postgresql+psycopg://"))
        self.assertTrue(settings.test_database_url.startswith("postgresql+psycopg://"))
        self.assertEqual(settings.test_database_url.rsplit("/", maxsplit=1)[-1], "ai_speech_test")
        self.assertFalse(settings.database_echo)
        self.assertEqual(settings.database_pool_size, 5)
        self.assertEqual(settings.database_max_overflow, 10)
        self.assertEqual(settings.redis_url, "redis://localhost:6379/0")
        self.assertEqual(settings.rq_queue_name, "ai-speech")
        self.assertEqual(settings.jwt_algorithm, "HS256")
        self.assertEqual(settings.access_token_expire_minutes, 30)
        self.assertEqual(settings.refresh_token_expire_days, 14)
        self.assertEqual(settings.local_storage_path, Path("storage"))

    def test_cors_origins_can_be_loaded_from_comma_separated_env_value(self) -> None:
        with patch.dict(
            environ,
            {"CORS_ORIGINS": "http://localhost:3000, http://localhost:8081"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(
            settings.cors_origins,
            ("http://localhost:3000", "http://localhost:8081"),
        )

    def test_api_prefix_must_start_with_slash(self) -> None:
        with patch.dict(environ, {"API_V1_PREFIX": "api/v1"}, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_production_requires_non_default_jwt_secret(self) -> None:
        with patch.dict(environ, {"ENVIRONMENT": "production"}, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

        with patch.dict(
            environ,
            {"ENVIRONMENT": "production", "JWT_SECRET_KEY": "replace-with-real-secret"},
            clear=True,
        ):
            settings = Settings(_env_file=None)
        self.assertTrue(settings.is_production)

    def test_get_settings_returns_cached_settings_instance(self) -> None:
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()

        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
