import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"


def _target_names(makefile_text: str) -> set[str]:
    target_pattern = re.compile(r"^([A-Za-z0-9_.-]+):", re.MULTILINE)
    return set(target_pattern.findall(makefile_text))


class MakefileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8")

    def test_development_makefile_exists(self) -> None:
        self.assertTrue(MAKEFILE_PATH.is_file())

    def test_core_development_targets_are_defined(self) -> None:
        targets = _target_names(self.makefile_text)

        self.assertGreaterEqual(
            targets,
            {
                "install",
                "install-dev",
                "test",
                "lint",
                "format",
                "typecheck",
                "dev",
                "check",
                "clean",
            },
        )

    def test_test_target_runs_current_unittest_suite(self) -> None:
        self.assertIn("PYTHONPATH=. $(PYTHON) -m unittest discover -s tests -v", self.makefile_text)

    def test_dev_target_uses_uvicorn_with_configurable_app_module(self) -> None:
        self.assertIn("APP_MODULE ?= app.main:app", self.makefile_text)
        self.assertIn("$(PYTHON) -m uvicorn $(APP_MODULE)", self.makefile_text)


if __name__ == "__main__":
    unittest.main()
