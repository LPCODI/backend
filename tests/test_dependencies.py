import re
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def _dependency_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].lower()


class DependencyFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with PYPROJECT_PATH.open("rb") as pyproject:
            cls.config = tomllib.load(pyproject)

    def test_python_312_runtime_is_required(self) -> None:
        self.assertEqual(self.config["project"]["requires-python"], ">=3.12,<3.13")

    def test_core_backend_dependencies_are_declared(self) -> None:
        dependencies = {
            _dependency_name(dependency): dependency
            for dependency in self.config["project"]["dependencies"]
        }

        for package_name in (
            "fastapi",
            "uvicorn",
            "pydantic",
            "pydantic-settings",
            "sqlalchemy",
            "psycopg",
            "alembic",
            "redis",
            "rq",
            "python-jose",
            "passlib",
            "python-multipart",
        ):
            with self.subTest(package_name=package_name):
                self.assertIn(package_name, dependencies)

        self.assertIn("pydantic>=2.", dependencies["pydantic"])
        self.assertIn("sqlalchemy>=2.", dependencies["sqlalchemy"])

    def test_optional_dependency_groups_cover_analysis_and_development_tools(self) -> None:
        optional_dependencies = self.config["project"]["optional-dependencies"]

        self.assertIn("dev", optional_dependencies)
        self.assertIn("document", optional_dependencies)
        self.assertIn("ai", optional_dependencies)
        self.assertIn("media", optional_dependencies)

        document_packages = {_dependency_name(item) for item in optional_dependencies["document"]}
        self.assertGreaterEqual(document_packages, {"python-pptx", "python-docx", "pymupdf"})


if __name__ == "__main__":
    unittest.main()
