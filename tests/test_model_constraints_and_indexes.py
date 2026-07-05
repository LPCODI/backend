import unittest

from sqlalchemy import Index, UniqueConstraint

from app.models import (
    AgentEvaluation,
    FinalReport,
    FillerWordEvent,
    GazeEvent,
    Job,
    JobStep,
    PoseEvent,
    Presentation,
    PresentationAnalysis,
    PresentationFile,
    Rehearsal,
    RehearsalMedia,
    Slide,
    SlideAnalysis,
    SlideScript,
    SlideTiming,
    SpeechEvent,
)


def unique_constraint_names(model: type) -> set[str]:
    return {
        constraint.name or ""
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def index_names(model: type) -> set[str]:
    return {index.name or "" for index in model.__table__.indexes if isinstance(index, Index)}


class ModelConstraintAndIndexTest(unittest.TestCase):
    def test_presentation_content_unique_constraints_are_declared(self) -> None:
        self.assertIn(
            "uq_presentation_files_storage_bucket_object_key",
            unique_constraint_names(PresentationFile),
        )
        self.assertIn("uq_slides_presentation_id_sort_order", unique_constraint_names(Slide))
        self.assertIn("uq_slides_presentation_id_slide_number", unique_constraint_names(Slide))
        self.assertIn(
            "uq_presentation_analyses_presentation_id_version",
            unique_constraint_names(PresentationAnalysis),
        )
        self.assertIn(
            "uq_slide_analyses_presentation_analysis_id_slide_id",
            unique_constraint_names(SlideAnalysis),
        )
        self.assertIn("uq_slide_timings_slide_id_version", unique_constraint_names(SlideTiming))
        self.assertIn("uq_slide_scripts_slide_id_version", unique_constraint_names(SlideScript))

    def test_rehearsal_job_and_report_unique_constraints_are_declared(self) -> None:
        self.assertIn(
            "uq_rehearsals_presentation_id_attempt_number",
            unique_constraint_names(Rehearsal),
        )
        self.assertIn(
            "uq_rehearsal_media_storage_bucket_object_key",
            unique_constraint_names(RehearsalMedia),
        )
        self.assertIn(
            "uq_agent_evaluations_rehearsal_id_agent_type_version",
            unique_constraint_names(AgentEvaluation),
        )
        self.assertIn("uq_final_reports_rehearsal_id_version", unique_constraint_names(FinalReport))
        self.assertIn("uq_job_steps_job_id_step_order", unique_constraint_names(JobStep))

    def test_core_lookup_indexes_are_declared(self) -> None:
        expected = {
            Presentation: "ix_presentations_user_id_status",
            PresentationFile: "ix_presentation_files_presentation_id_status",
            Slide: "ix_slides_presentation_id_excluded_sort_order",
            PresentationAnalysis: "ix_presentation_analyses_presentation_id_status",
            SlideTiming: "ix_slide_timings_slide_id_is_active",
            SlideScript: "ix_slide_scripts_slide_id_is_active",
            Rehearsal: "ix_rehearsals_presentation_id_status",
            RehearsalMedia: "ix_rehearsal_media_rehearsal_id_media_type_status",
            FillerWordEvent: "ix_filler_word_events_audio_analysis_id_start_seconds",
            SpeechEvent: "ix_speech_events_audio_analysis_id_event_type",
            PoseEvent: "ix_pose_events_pose_analysis_id_event_type",
            GazeEvent: "ix_gaze_events_gaze_analysis_id_event_type",
            AgentEvaluation: "ix_agent_evaluations_rehearsal_id_agent_type_status",
            FinalReport: "ix_final_reports_rehearsal_id_is_latest",
            Job: "ix_jobs_user_id_status",
        }

        for model, expected_index in expected.items():
            with self.subTest(model=model.__name__):
                self.assertIn(expected_index, index_names(model))

        self.assertIn("ix_jobs_presentation_id_job_type_status", index_names(Job))
        self.assertIn("ix_jobs_rehearsal_id_job_type_status", index_names(Job))


if __name__ == "__main__":
    unittest.main()
