import unittest
from uuid import UUID, uuid4

from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db import Base
from app.domain import JobStatus
from app.models import Job, JobStep, Presentation, Rehearsal, User


class JobModelTest(unittest.TestCase):
    def test_jobs_table_matches_specification(self) -> None:
        columns = Job.__table__.columns

        self.assertEqual(Job.__tablename__, "jobs")
        self.assertTrue(columns["job_id"].primary_key)
        self.assertFalse(columns["user_id"].nullable)
        self.assertTrue(columns["user_id"].index)
        self.assertTrue(columns["presentation_id"].nullable)
        self.assertTrue(columns["presentation_id"].index)
        self.assertTrue(columns["rehearsal_id"].nullable)
        self.assertTrue(columns["rehearsal_id"].index)
        self.assertEqual(columns["job_type"].type.length, 50)
        self.assertTrue(columns["job_type"].index)
        self.assertEqual(columns["status"].type.length, 30)
        self.assertTrue(columns["status"].index)
        self.assertFalse(columns["progress"].nullable)
        self.assertEqual(columns["current_step"].type.length, 100)
        self.assertEqual(columns["error_code"].type.length, 100)
        self.assertEqual(columns["worker_task_id"].type.length, 255)
        self.assertTrue(columns["worker_task_id"].index)
        self.assertFalse(columns["created_at"].nullable)

    def test_job_steps_table_matches_specification(self) -> None:
        columns = JobStep.__table__.columns

        self.assertEqual(JobStep.__tablename__, "job_steps")
        self.assertTrue(columns["job_step_id"].primary_key)
        self.assertFalse(columns["job_id"].nullable)
        self.assertTrue(columns["job_id"].index)
        self.assertEqual(columns["step_name"].type.length, 100)
        self.assertFalse(columns["step_name"].nullable)
        self.assertFalse(columns["step_order"].nullable)
        self.assertTrue(columns["step_order"].index)
        self.assertEqual(columns["status"].type.length, 30)
        self.assertTrue(columns["status"].index)
        self.assertFalse(columns["progress"].nullable)
        self.assertTrue(columns["started_at"].nullable)
        self.assertTrue(columns["completed_at"].nullable)

    def test_postgresql_ddl_contains_uuid_foreign_keys_and_jsonb(self) -> None:
        job_ddl = str(CreateTable(Job.__table__).compile(dialect=postgresql.dialect())).upper()
        step_ddl = str(CreateTable(JobStep.__table__).compile(dialect=postgresql.dialect())).upper()

        self.assertIn("JOB_ID UUID DEFAULT GEN_RANDOM_UUID() NOT NULL", job_ddl)
        self.assertIn("CONSTRAINT PK_JOBS PRIMARY KEY (JOB_ID)", job_ddl)
        self.assertIn("FOREIGN KEY(USER_ID) REFERENCES USERS (USER_ID) ON DELETE CASCADE", job_ddl)
        self.assertIn("FOREIGN KEY(PRESENTATION_ID) REFERENCES PRESENTATIONS", job_ddl)
        self.assertIn("FOREIGN KEY(REHEARSAL_ID) REFERENCES REHEARSALS", job_ddl)
        self.assertIn("REQUEST_PAYLOAD JSONB", job_ddl)
        self.assertIn("RESULT_PAYLOAD JSONB", job_ddl)
        self.assertIn("CONSTRAINT PK_JOB_STEPS PRIMARY KEY (JOB_STEP_ID)", step_ddl)
        self.assertIn("JOB_ID UUID NOT NULL", step_ddl)
        self.assertIn("FOREIGN KEY(JOB_ID) REFERENCES JOBS (JOB_ID) ON DELETE CASCADE", step_ddl)

    def test_models_create_and_persist_job_graph(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        self.assertTrue(inspector.has_table("jobs"))
        self.assertTrue(inspector.has_table("job_steps"))

        with Session(engine) as session:
            user = User(user_id=1, email="jobs@example.com", password_hash="hash", name="Presenter")
            presentation = Presentation(
                presentation_id=1,
                user=user,
                title="AI Speech Demo",
                total_duration_seconds=600,
                qa_duration_seconds=120,
                presentation_duration_seconds=480,
            )
            rehearsal = Rehearsal(rehearsal_id=1, presentation=presentation, attempt_number=1)
            job_id = uuid4()
            job = Job(
                job_id=job_id,
                user=user,
                presentation=presentation,
                rehearsal=rehearsal,
                job_type="REHEARSAL_ANALYSIS",
                status=JobStatus.QUEUED,
                progress=25,
                current_step="AUDIO_ANALYSIS",
                request_payload={"tasks": ["AUDIO", "POSE", "GAZE"]},
                worker_task_id="rq:job:1",
            )
            job.steps = [
                JobStep(
                    job_step_id=1,
                    step_name="AUDIO_ANALYSIS",
                    step_order=1,
                    status=JobStatus.COMPLETED,
                    progress=100,
                ),
                JobStep(
                    job_step_id=2,
                    step_name="GAZE_ANALYSIS",
                    step_order=2,
                    status=JobStatus.PROCESSING,
                    progress=25,
                ),
            ]
            session.add_all([user, presentation, rehearsal, job])
            session.commit()

            stored = session.get(Job, job_id)
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertIsInstance(stored.job_id, UUID)
            self.assertEqual(stored.status, JobStatus.QUEUED.value)
            self.assertEqual(stored.request_payload, {"tasks": ["AUDIO", "POSE", "GAZE"]})
            self.assertEqual(user.jobs[0].job_type, "REHEARSAL_ANALYSIS")
            self.assertEqual(presentation.jobs[0].current_step, "AUDIO_ANALYSIS")
            self.assertEqual(rehearsal.jobs[0].worker_task_id, "rq:job:1")
            self.assertEqual([step.step_name for step in stored.steps], ["AUDIO_ANALYSIS", "GAZE_ANALYSIS"])
            self.assertEqual(stored.steps[1].status, JobStatus.PROCESSING.value)


if __name__ == "__main__":
    unittest.main()
