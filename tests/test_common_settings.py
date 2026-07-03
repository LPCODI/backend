import unittest
from os import environ
from unittest.mock import patch

from app.core import AppEnvironment, Settings, get_settings
from app.main import create_app


class CommonSettingsTest(unittest.TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_core_package_exports_shared_settings_types(self) -> None:
        self.assertEqual(Settings.__name__, "Settings")
        self.assertEqual(AppEnvironment.TEST, "test")
        self.assertTrue(callable(get_settings))

    def test_get_settings_loads_environment_once_until_cache_is_cleared(self) -> None:
        get_settings.cache_clear()
        with patch.dict(environ, {"APP_NAME": "Cached Settings Probe"}, clear=True):
            first = get_settings()

        with patch.dict(environ, {"APP_NAME": "Changed Settings Probe"}, clear=True):
            second = get_settings()

        self.assertIs(first, second)
        self.assertEqual(second.app_name, "Cached Settings Probe")

        get_settings.cache_clear()
        with patch.dict(environ, {"APP_NAME": "Changed Settings Probe"}, clear=True):
            reloaded = get_settings()

        self.assertIsNot(first, reloaded)
        self.assertEqual(reloaded.app_name, "Changed Settings Probe")

    def test_create_app_exposes_the_effective_settings_instance(self) -> None:
        settings = Settings(
            app_name="Common Settings App",
            environment=AppEnvironment.TEST,
            api_v1_prefix="/api/v1/",
            _env_file=None,
        )

        app = create_app(settings=settings)

        self.assertIs(app.state.settings, settings)
        self.assertEqual(app.state.settings.environment, AppEnvironment.TEST)
        self.assertEqual(app.state.settings.api_v1_prefix, "/api/v1")

    def test_default_settings_contract_matches_backend_stack(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.api_v1_prefix, "/api/v1")
        self.assertEqual(settings.storage_backend, "local")
        self.assertEqual(settings.database_url.split("://", maxsplit=1)[0], "postgresql+psycopg")
        self.assertTrue(settings.redis_url.startswith("redis://"))
        self.assertGreater(settings.access_token_expire_minutes, 0)
        self.assertGreater(settings.refresh_token_expire_days, 0)


if __name__ == "__main__":
    unittest.main()
