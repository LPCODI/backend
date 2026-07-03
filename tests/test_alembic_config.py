import configparser
import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy import MetaData

from app.core import Settings, get_settings
from app.db import Base
from app.db.migrations import get_migration_database_url, get_migration_metadata


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class AlembicConfigTest(unittest.TestCase):
    def test_alembic_files_are_present(self) -> None:
        self.assertTrue((BACKEND_ROOT / "alembic.ini").is_file())
        self.assertTrue((BACKEND_ROOT / "alembic" / "env.py").is_file())
        self.assertTrue((BACKEND_ROOT / "alembic" / "script.py.mako").is_file())
        self.assertTrue((BACKEND_ROOT / "alembic" / "versions").is_dir())

    def test_alembic_ini_points_to_project_migration_directory(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(BACKEND_ROOT / "alembic.ini")

        self.assertEqual(parser["alembic"]["script_location"], "alembic")
        self.assertEqual(parser["alembic"]["prepend_sys_path"], ".")
        self.assertTrue(parser["alembic"]["sqlalchemy.url"].startswith("postgresql+psycopg://"))

    def test_migration_helpers_use_app_settings_and_base_metadata(self) -> None:
        settings = Settings(
            database_url="sqlite+pysqlite:///:memory:",
            _env_file=None,
        )

        self.assertEqual(get_migration_database_url(settings), "sqlite+pysqlite:///:memory:")
        self.assertIs(get_migration_metadata(), Base.metadata)
        self.assertIsInstance(get_migration_metadata(), MetaData)

    def test_alembic_env_targets_application_metadata(self) -> None:
        env_source = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

        self.assertIn("get_migration_database_url", env_source)
        self.assertIn("get_migration_metadata", env_source)
        self.assertIn("target_metadata = get_migration_metadata()", env_source)
        self.assertIn("compare_type=True", env_source)
        self.assertIn("compare_server_default=True", env_source)

    def test_initial_migration_upgrade_and_downgrade_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_url = f"sqlite+pysqlite:///{Path(tmp_dir) / 'migration-test.db'}"
            previous_database_url = os.environ.get("DATABASE_URL")
            os.environ["DATABASE_URL"] = database_url
            get_settings.cache_clear()

            try:
                alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
                alembic_config.set_main_option(
                    "script_location",
                    str(BACKEND_ROOT / "alembic"),
                )

                command.upgrade(alembic_config, "head")

                engine = create_engine(database_url)
                with engine.connect() as connection:
                    self.assertTrue(inspect(connection).has_table("alembic_version"))
                    self.assertTrue(inspect(connection).has_table("users"))
                    self.assertTrue(inspect(connection).has_table("refresh_tokens"))
                    self.assertTrue(inspect(connection).has_table("presentations"))
                    self.assertTrue(inspect(connection).has_table("presentation_files"))
                    self.assertTrue(inspect(connection).has_table("slides"))
                    self.assertTrue(inspect(connection).has_table("presentation_analyses"))
                    self.assertTrue(inspect(connection).has_table("slide_analyses"))
                    self.assertTrue(inspect(connection).has_table("slide_timings"))
                    self.assertTrue(inspect(connection).has_table("slide_scripts"))
                    self.assertTrue(inspect(connection).has_table("rehearsals"))
                    self.assertTrue(inspect(connection).has_table("rehearsal_media"))
                    self.assertTrue(inspect(connection).has_table("audio_analyses"))
                    self.assertTrue(inspect(connection).has_table("filler_word_events"))
                    self.assertTrue(inspect(connection).has_table("speech_events"))
                    self.assertTrue(inspect(connection).has_table("pose_analyses"))
                    self.assertTrue(inspect(connection).has_table("pose_events"))
                    self.assertTrue(inspect(connection).has_table("gaze_analyses"))
                    self.assertTrue(inspect(connection).has_table("gaze_events"))
                    self.assertTrue(inspect(connection).has_table("rehearsal_slide_results"))
                    self.assertTrue(inspect(connection).has_table("agent_evaluations"))
                    self.assertTrue(inspect(connection).has_table("evaluation_criteria"))
                    self.assertTrue(inspect(connection).has_table("evaluation_priorities"))
                    self.assertTrue(inspect(connection).has_table("evaluation_priority_slides"))
                    self.assertTrue(inspect(connection).has_table("qa_sessions"))
                    self.assertTrue(inspect(connection).has_table("qa_questions"))
                    self.assertTrue(inspect(connection).has_table("qa_question_slides"))
                    self.assertTrue(inspect(connection).has_table("qa_answers"))
                    self.assertTrue(inspect(connection).has_table("qa_answer_evaluations"))
                    self.assertTrue(inspect(connection).has_table("final_reports"))
                    self.assertTrue(inspect(connection).has_table("report_scores"))
                    self.assertTrue(inspect(connection).has_table("rehearsal_comparisons"))
                    self.assertTrue(inspect(connection).has_table("comparison_metrics"))
                    self.assertTrue(inspect(connection).has_table("jobs"))
                    self.assertTrue(inspect(connection).has_table("job_steps"))
                    current_revision = connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one()

                self.assertEqual(current_revision, "20260703_0007")

                command.downgrade(alembic_config, "base")

                with engine.connect() as connection:
                    remaining_revisions = connection.execute(
                        text("SELECT COUNT(*) FROM alembic_version")
                    ).scalar_one()

                self.assertEqual(remaining_revisions, 0)
            finally:
                if previous_database_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous_database_url
                get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
