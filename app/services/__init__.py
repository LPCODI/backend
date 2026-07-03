"""Service contracts and MVP stubs for replaceable analysis engines."""

from app.services.interfaces import (
    AnalysisArtifact,
    AnalysisInput,
    AgentEvaluationService,
    AudioAnalysisService,
    DocumentParseResult,
    DocumentParserService,
    GazeAnalysisService,
    PoseAnalysisService,
    QaGenerationService,
    ReportGenerationService,
    ScriptGenerationService,
    SlideAnalysisService,
)
from app.services.stub_policy import (
    DEFAULT_STUB_POLICY,
    MVP_STUB_SERVICE_DESCRIPTORS,
    StubPolicy,
    StubServiceDescriptor,
    get_stub_service_descriptors,
)
from app.services.stubs import DeterministicMvpAnalysisStub

__all__ = [
    "AnalysisArtifact",
    "AnalysisInput",
    "AgentEvaluationService",
    "AudioAnalysisService",
    "DEFAULT_STUB_POLICY",
    "DeterministicMvpAnalysisStub",
    "DocumentParseResult",
    "DocumentParserService",
    "GazeAnalysisService",
    "MVP_STUB_SERVICE_DESCRIPTORS",
    "PoseAnalysisService",
    "QaGenerationService",
    "ReportGenerationService",
    "ScriptGenerationService",
    "SlideAnalysisService",
    "StubPolicy",
    "StubServiceDescriptor",
    "get_stub_service_descriptors",
]
