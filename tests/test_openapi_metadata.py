import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import API_VERSION, OPENAPI_TAGS, Settings, build_openapi_metadata


class OpenApiMetadataTest(unittest.TestCase):
    def test_metadata_uses_settings_app_name_and_fixed_api_version(self) -> None:
        metadata = build_openapi_metadata(
            Settings(app_name="Custom Speech API", _env_file=None),
        )

        self.assertEqual(metadata["title"], "Custom Speech API")
        self.assertEqual(metadata["version"], API_VERSION)
        self.assertEqual(metadata["docs_url"], "/docs")
        self.assertEqual(metadata["openapi_url"], "/openapi.json")

    def test_metadata_documents_fixed_professor_project_context(self) -> None:
        description = str(build_openapi_metadata(Settings(_env_file=None))["description"])

        self.assertIn("대학 프로젝트", description)
        self.assertIn("교수님", description)
        self.assertIn("발표 대상, 발표 목적, 발표 상황, 말투", description)
        self.assertIn("/api/v1", description)

    def test_all_expected_api_groups_are_registered_as_openapi_tags(self) -> None:
        tag_names = {tag["name"] for tag in OPENAPI_TAGS}

        self.assertEqual(len(OPENAPI_TAGS), len(tag_names))
        self.assertTrue(
            {
                "auth",
                "presentations",
                "files",
                "slides",
                "analysis",
                "timings",
                "scripts",
                "rehearsals",
                "media",
                "audio-analysis",
                "video-analysis",
                "evaluations",
                "qa",
                "reports",
                "jobs",
                "system",
            }.issubset(tag_names),
        )

    def test_fastapi_openapi_schema_exposes_configured_metadata(self) -> None:
        app = FastAPI(**build_openapi_metadata(Settings(_env_file=None)))
        schema = TestClient(app).get("/openapi.json").json()

        self.assertEqual(schema["info"]["title"], "AI Speech Backend")
        self.assertEqual(schema["info"]["version"], API_VERSION)
        self.assertEqual(schema["tags"], OPENAPI_TAGS)


if __name__ == "__main__":
    unittest.main()
