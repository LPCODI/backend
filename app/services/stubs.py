"""Deterministic MVP implementations of replaceable service interfaces."""

from __future__ import annotations

from app.domain import DEFAULT_PRESENTATION_CONTEXT
from app.services.interfaces import AnalysisArtifact, AnalysisInput, DocumentParseResult


class DeterministicMvpAnalysisStub:
    """Single deterministic stub used until real AI/media adapters are wired."""

    provider = "deterministic-mvp-stub"
    version = "0.1.0"

    async def parse(self, source: AnalysisInput) -> DocumentParseResult:
        title = source.metadata.get("title") or source.text or source.resource_id
        return DocumentParseResult(
            provider=self.provider,
            version=self.version,
            slides=(
                {
                    "slideNumber": 1,
                    "title": str(title),
                    "body": source.text or "",
                    "images": [],
                    "tables": [],
                    "graphs": [],
                },
            ),
            warnings=("MVP stub result; replace with document parser adapter.",),
        )

    async def analyze_slides(self, presentation: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "slide_analysis",
            {
                "presentationContext": DEFAULT_PRESENTATION_CONTEXT.value,
                "keywords": [],
                "missingExplanations": [],
                "duplicates": [],
                "connectionIssues": [],
                "expectedProfessorQuestions": [],
            },
        )

    async def generate_script(self, presentation: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "script_generation",
            {
                "presentationContext": DEFAULT_PRESENTATION_CONTEXT.value,
                "script": "교수님 앞 대학 프로젝트 발표용 MVP 대본 stub입니다.",
            },
        )

    async def analyze_audio(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "audio_analysis",
            {
                "transcript": "",
                "fillerWords": [],
                "speechSpeedWpm": None,
                "silenceSegments": [],
                "omissions": [],
            },
        )

    async def analyze_pose(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "pose_analysis",
            {
                "postureScore": None,
                "events": [],
            },
        )

    async def analyze_gaze(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "gaze_analysis",
            {
                "gazeDistribution": {
                    "professor": None,
                    "screen": None,
                    "floor": None,
                },
                "events": [],
            },
        )

    async def evaluate_rehearsal(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "agent_evaluation",
            {
                "professor": {"score": None, "feedback": "MVP stub evaluation."},
                "student": {"score": None, "feedback": "MVP stub evaluation."},
                "finalJudge": {"score": None, "feedback": "MVP stub evaluation."},
            },
        )

    async def generate_questions(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "qa_generation",
            {
                "questions": [
                    {
                        "question": "이 프로젝트의 핵심 차별점은 무엇인가요?",
                        "intent": "대학 프로젝트 평가 관점의 MVP stub 질문",
                    }
                ],
            },
        )

    async def generate_report(self, rehearsal: AnalysisInput) -> AnalysisArtifact:
        return self._artifact(
            "report_generation",
            {
                "summary": "MVP stub report.",
                "scores": {},
                "improvementPriorities": [],
                "pdfGenerated": False,
            },
        )

    def _artifact(self, capability: str, result: dict[str, object]) -> AnalysisArtifact:
        return AnalysisArtifact(
            provider=self.provider,
            version=self.version,
            result={"capability": capability, **result},
            warnings=("MVP stub result; replace with real service adapter.",),
        )
