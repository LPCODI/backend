"""Replaceable service interfaces for expensive AI and media processing.

The API and persistence layers should depend on these protocols instead of
directly importing Whisper, LLM, YOLO, MediaPipe, OpenCV, FFmpeg, or document
parsing libraries. Concrete adapters can replace the MVP stubs without changing
endpoint contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    """Minimal input shared by async AI/media service adapters."""

    resource_id: str
    file_path: Path | None = None
    text: str | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisArtifact:
    """Normalized output for AI/media service adapters."""

    provider: str
    version: str
    result: JsonObject
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentParseResult:
    """Parsed presentation source that can later be persisted as slides."""

    provider: str
    version: str
    slides: tuple[JsonObject, ...]
    warnings: tuple[str, ...] = ()


@runtime_checkable
class DocumentParserService(Protocol):
    async def parse(self, source: AnalysisInput) -> DocumentParseResult:
        """Extract slide-like structure from PPT/PPTX/PDF/DOC/DOCX files."""


@runtime_checkable
class SlideAnalysisService(Protocol):
    async def analyze_slides(self, presentation: AnalysisInput) -> AnalysisArtifact:
        """Analyze keywords, complexity, missing explanations, and links."""


@runtime_checkable
class ScriptGenerationService(Protocol):
    async def generate_script(self, presentation: AnalysisInput) -> AnalysisArtifact:
        """Generate professor-facing presentation scripts."""


@runtime_checkable
class AudioAnalysisService(Protocol):
    async def analyze_audio(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Analyze STT, filler words, speed, silence, and omissions."""


@runtime_checkable
class PoseAnalysisService(Protocol):
    async def analyze_pose(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Analyze body posture and repeated pose-related behavior."""


@runtime_checkable
class GazeAnalysisService(Protocol):
    async def analyze_gaze(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Analyze eye contact, head direction, and gaze-related behavior."""


@runtime_checkable
class AgentEvaluationService(Protocol):
    async def evaluate_rehearsal(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Evaluate a rehearsal from professor, student, or final-judge views."""


@runtime_checkable
class QaGenerationService(Protocol):
    async def generate_questions(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Generate likely professor questions and answer guidance."""


@runtime_checkable
class ReportGenerationService(Protocol):
    async def generate_report(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        """Generate the final rehearsal report and improvement summary."""
