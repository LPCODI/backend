import unittest

from pydantic import BaseModel

from app.domain import AgentType, JobStatus, PresentationStatus, RehearsalStatus


class StatusEnvelope(BaseModel):
    presentation_status: PresentationStatus
    job_status: JobStatus
    rehearsal_status: RehearsalStatus
    agent_type: AgentType


class StatusEnumTest(unittest.TestCase):
    def test_presentation_status_values_match_api_overview(self) -> None:
        self.assertEqual(
            tuple(status.value for status in PresentationStatus),
            (
                "DRAFT",
                "FILE_UPLOADED",
                "PARSING",
                "PARSED",
                "ANALYZING",
                "ANALYZED",
                "SCRIPT_GENERATING",
                "SCRIPT_READY",
                "REHEARSAL_READY",
                "COMPLETED",
                "FAILED",
            ),
        )

    def test_job_status_values_match_api_overview(self) -> None:
        self.assertEqual(
            tuple(status.value for status in JobStatus),
            (
                "PENDING",
                "QUEUED",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
            ),
        )

    def test_rehearsal_status_values_match_api_overview(self) -> None:
        self.assertEqual(
            tuple(status.value for status in RehearsalStatus),
            (
                "CREATED",
                "UPLOADING",
                "UPLOADED",
                "ANALYZING",
                "ANALYZED",
                "EVALUATING",
                "COMPLETED",
                "FAILED",
            ),
        )

    def test_agent_type_is_limited_to_product_scope(self) -> None:
        self.assertEqual(
            tuple(agent.value for agent in AgentType),
            ("PROFESSOR", "STUDENT", "FINAL_JUDGE"),
        )

    def test_enums_are_string_compatible(self) -> None:
        self.assertIsInstance(PresentationStatus.DRAFT, str)
        self.assertEqual(str(JobStatus.QUEUED), "QUEUED")
        self.assertEqual(RehearsalStatus.CREATED, "CREATED")
        self.assertEqual(AgentType.PROFESSOR, "PROFESSOR")

    def test_pydantic_serializes_status_enums_as_strings(self) -> None:
        envelope = StatusEnvelope(
            presentation_status=PresentationStatus.DRAFT,
            job_status=JobStatus.QUEUED,
            rehearsal_status=RehearsalStatus.CREATED,
            agent_type=AgentType.FINAL_JUDGE,
        )

        self.assertEqual(
            envelope.model_dump(mode="json"),
            {
                "presentation_status": "DRAFT",
                "job_status": "QUEUED",
                "rehearsal_status": "CREATED",
                "agent_type": "FINAL_JUDGE",
            },
        )


if __name__ == "__main__":
    unittest.main()
