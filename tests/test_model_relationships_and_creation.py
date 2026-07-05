import unittest

from sqlalchemy import create_engine, inspect as inspect_engine
from sqlalchemy import inspect as inspect_mapper

from app.db import Base
from app.models import (
    AgentEvaluation,
    AudioAnalysis,
    ComparisonMetric,
    EvaluationCriterion,
    EvaluationPriority,
    EvaluationPrioritySlide,
    FinalReport,
    FillerWordEvent,
    GazeAnalysis,
    GazeEvent,
    Job,
    JobStep,
    PoseAnalysis,
    PoseEvent,
    Presentation,
    PresentationAnalysis,
    PresentationFile,
    QaAnswer,
    QaAnswerEvaluation,
    QaQuestion,
    QaQuestionSlide,
    QaSession,
    RefreshToken,
    Rehearsal,
    RehearsalComparison,
    RehearsalMedia,
    RehearsalSlideResult,
    ReportScore,
    Slide,
    SlideAnalysis,
    SlideScript,
    SlideTiming,
    SpeechEvent,
    User,
)


EXPECTED_TABLES = {
    "agent_evaluations",
    "audio_analyses",
    "comparison_metrics",
    "evaluation_criteria",
    "evaluation_priorities",
    "evaluation_priority_slides",
    "filler_word_events",
    "final_reports",
    "gaze_analyses",
    "gaze_events",
    "job_steps",
    "jobs",
    "pose_analyses",
    "pose_events",
    "presentation_analyses",
    "presentation_files",
    "presentations",
    "qa_answer_evaluations",
    "qa_answers",
    "qa_question_slides",
    "qa_questions",
    "qa_sessions",
    "refresh_tokens",
    "rehearsal_comparisons",
    "rehearsal_media",
    "rehearsal_slide_results",
    "rehearsals",
    "report_scores",
    "slide_analyses",
    "slide_scripts",
    "slide_timings",
    "slides",
    "speech_events",
    "users",
}


class ModelRelationshipAndCreationTest(unittest.TestCase):
    def test_all_documented_tables_are_registered_and_creatable(self) -> None:
        self.assertTrue(EXPECTED_TABLES.issubset(set(Base.metadata.tables)))

        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect_engine(engine)
        self.assertTrue(EXPECTED_TABLES.issubset(set(inspector.get_table_names())))

    def test_core_relationships_match_database_design(self) -> None:
        expected_relationships = {
            User: {
                "refresh_tokens": RefreshToken,
                "presentations": Presentation,
                "jobs": Job,
            },
            Presentation: {
                "files": PresentationFile,
                "slides": Slide,
                "analyses": PresentationAnalysis,
                "rehearsals": Rehearsal,
                "rehearsal_comparisons": RehearsalComparison,
                "jobs": Job,
            },
            PresentationFile: {"slides": Slide},
            PresentationAnalysis: {"slide_analyses": SlideAnalysis},
            Slide: {
                "analyses": SlideAnalysis,
                "timings": SlideTiming,
                "scripts": SlideScript,
                "rehearsal_results": RehearsalSlideResult,
                "evaluation_priority_links": EvaluationPrioritySlide,
                "qa_question_links": QaQuestionSlide,
            },
            Rehearsal: {
                "media": RehearsalMedia,
                "audio_analysis": AudioAnalysis,
                "pose_analysis": PoseAnalysis,
                "gaze_analysis": GazeAnalysis,
                "slide_results": RehearsalSlideResult,
                "agent_evaluations": AgentEvaluation,
                "qa_sessions": QaSession,
                "final_reports": FinalReport,
                "base_comparisons": RehearsalComparison,
                "target_comparisons": RehearsalComparison,
                "jobs": Job,
            },
            AudioAnalysis: {
                "filler_word_events": FillerWordEvent,
                "speech_events": SpeechEvent,
            },
            PoseAnalysis: {"events": PoseEvent},
            GazeAnalysis: {"events": GazeEvent},
            AgentEvaluation: {
                "criteria": EvaluationCriterion,
                "priorities": EvaluationPriority,
            },
            EvaluationPriority: {"slide_links": EvaluationPrioritySlide},
            QaSession: {"questions": QaQuestion},
            QaQuestion: {
                "slide_links": QaQuestionSlide,
                "answers": QaAnswer,
            },
            QaAnswer: {"evaluation": QaAnswerEvaluation},
            FinalReport: {"scores": ReportScore},
            RehearsalComparison: {"metrics": ComparisonMetric},
            Job: {"steps": JobStep},
        }

        for model, relationships in expected_relationships.items():
            mapper_relationships = inspect_mapper(model).relationships
            for relationship_name, expected_target in relationships.items():
                with self.subTest(model=model.__name__, relationship=relationship_name):
                    relationship = mapper_relationships[relationship_name]
                    self.assertIs(relationship.mapper.class_, expected_target)
                    self.assertIsNotNone(relationship.back_populates)

    def test_one_to_one_relationships_are_not_collections(self) -> None:
        expected_scalar_relationships = (
            (Rehearsal, "audio_analysis"),
            (Rehearsal, "pose_analysis"),
            (Rehearsal, "gaze_analysis"),
            (QaAnswer, "evaluation"),
        )

        for model, relationship_name in expected_scalar_relationships:
            with self.subTest(model=model.__name__, relationship=relationship_name):
                relationship = inspect_mapper(model).relationships[relationship_name]
                self.assertFalse(relationship.uselist)


if __name__ == "__main__":
    unittest.main()
