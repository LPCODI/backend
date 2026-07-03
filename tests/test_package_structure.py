import importlib
import unittest

from app import APP_PACKAGE_MODULES


class PackageStructureTest(unittest.TestCase):
    def test_fastapi_application_package_boundaries_are_importable(self) -> None:
        expected_modules = (
            "app.api",
            "app.api.v1",
            "app.api.v1.routers",
            "app.core",
            "app.db",
            "app.domain",
            "app.models",
            "app.repositories",
            "app.schemas",
            "app.services",
            "app.workers",
        )

        self.assertEqual(APP_PACKAGE_MODULES, expected_modules)
        for module_name in expected_modules:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))


if __name__ == "__main__":
    unittest.main()
