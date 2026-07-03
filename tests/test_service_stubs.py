import asyncio
import unittest

from app.domain import DEFAULT_PRESENTATION_CONTEXT
from app.services import (
    AgentEvaluationService,
    AnalysisInput,
    AudioAnalysisService,
    DEFAULT_STUB_POLICY,
    DeterministicMvpAnalysisStub,
    DocumentParserService,
    GazeAnalysisService,
    PoseAnalysisService,
    QaGenerationService,
    ReportGenerationService,
    ScriptGenerationService,
    SlideAnalysisService,
    StubPolicy,
    get_stub_service_descriptors,
)


class ServiceStubPolicyTest(unittest.TestCase):
    def test_stub_policy_is_explicit_and_deterministic(self) -> None:
        self.assertEqual(DEFAULT_STUB_POLICY, StubPolicy.DETERMINISTIC_MVP)
        self.assertEqual(DEFAULT_STUB_POLICY.value, "DETERMINISTIC_MVP")

    def test_stub_descriptors_cover_expensive_ai_and_media_capabilities(self) -> None:
        capabilities = {descriptor.capability for descriptor in get_stub_service_descriptors()}
        self.assertEqual(
            capabilities,
            {
                "document_parsing",
                "slide_analysis",
                "script_generation",
                "audio_analysis",
                "pose_analysis",
                "gaze_analysis",
                "agent_evaluation",
                "qa_generation",
                "report_generation",
            },
        )

    def test_deterministic_stub_satisfies_all_replaceable_interfaces(self) -> None:
        stub = DeterministicMvpAnalysisStub()
        for service_type in (
            DocumentParserService,
            SlideAnalysisService,
            ScriptGenerationService,
            AudioAnalysisService,
            PoseAnalysisService,
            GazeAnalysisService,
            AgentEvaluationService,
            QaGenerationService,
            ReportGenerationService,
        ):
            self.assertIsInstance(stub, service_type)

    def test_deterministic_stub_returns_fixed_context_for_script_generation(self) -> None:
        stub = DeterministicMvpAnalysisStub()
        artifact = asyncio.run(stub.generate_script(AnalysisInput(resource_id="presentation-1")))

        self.assertEqual(artifact.provider, "deterministic-mvp-stub")
        self.assertEqual(
            artifact.result["presentationContext"],
            DEFAULT_PRESENTATION_CONTEXT.value,
        )
        self.assertIn("MVP stub", artifact.warnings[0])


if __name__ == "__main__":
    unittest.main()
