"""MVP stub policy for external AI and media processing services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StubPolicy(StrEnum):
    DETERMINISTIC_MVP = "DETERMINISTIC_MVP"


DEFAULT_STUB_POLICY = StubPolicy.DETERMINISTIC_MVP


@dataclass(frozen=True, slots=True)
class StubServiceDescriptor:
    capability: str
    interface_name: str
    policy: StubPolicy
    replacement_target: str
    mvp_behavior: str


MVP_STUB_SERVICE_DESCRIPTORS: tuple[StubServiceDescriptor, ...] = (
    StubServiceDescriptor(
        capability="document_parsing",
        interface_name="DocumentParserService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="python-pptx, PyMuPDF, python-docx, LibreOffice Headless",
        mvp_behavior="Return one synthetic slide from supplied text or file metadata.",
    ),
    StubServiceDescriptor(
        capability="slide_analysis",
        interface_name="SlideAnalysisService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="LLM API or local NLP pipeline",
        mvp_behavior="Return deterministic keyword, complexity, and question placeholders.",
    ),
    StubServiceDescriptor(
        capability="script_generation",
        interface_name="ScriptGenerationService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="LLM API",
        mvp_behavior="Return a professor-facing script placeholder using the fixed context.",
    ),
    StubServiceDescriptor(
        capability="audio_analysis",
        interface_name="AudioAnalysisService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="FFmpeg plus Whisper API or Faster-Whisper",
        mvp_behavior="Return empty transcript and neutral speech metrics.",
    ),
    StubServiceDescriptor(
        capability="pose_analysis",
        interface_name="PoseAnalysisService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="YOLO Pose and OpenCV",
        mvp_behavior="Return neutral posture score with no behavior events.",
    ),
    StubServiceDescriptor(
        capability="gaze_analysis",
        interface_name="GazeAnalysisService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="MediaPipe face mesh and OpenCV",
        mvp_behavior="Return neutral gaze distribution with no behavior events.",
    ),
    StubServiceDescriptor(
        capability="agent_evaluation",
        interface_name="AgentEvaluationService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="LLM API",
        mvp_behavior="Return professor, student, and final-judge placeholder feedback.",
    ),
    StubServiceDescriptor(
        capability="qa_generation",
        interface_name="QaGenerationService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="LLM API",
        mvp_behavior="Return deterministic professor-style expected questions.",
    ),
    StubServiceDescriptor(
        capability="report_generation",
        interface_name="ReportGenerationService",
        policy=DEFAULT_STUB_POLICY,
        replacement_target="LLM API and PDF renderer",
        mvp_behavior="Return deterministic summary data without creating a PDF file.",
    ),
)


def get_stub_service_descriptors() -> tuple[StubServiceDescriptor, ...]:
    return MVP_STUB_SERVICE_DESCRIPTORS
