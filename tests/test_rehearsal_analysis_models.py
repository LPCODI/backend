import unittest
from decimal import Decimal

from sqlalchemy import UniqueConstraint, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db import Base
from app.domain import RehearsalStatus
from app.models import (
    AudioAnalysis,
    FillerWordEvent,
    GazeAnalysis,
    GazeEvent,
    PoseAnalysis,
    PoseEvent,
    Presentation,
    PresentationFile,
    Rehearsal,
    RehearsalMedia,
    RehearsalSlideResult,
    Slide,
    SpeechEvent,
    User,
)


class RehearsalAnalysisModelTest(unittest.TestCase):
    def test_rehearsal_tables_match_specification(self) -> None:
        self.assertEqual(Rehearsal.__tablename__, "rehearsals")
        self.assertTrue(Rehearsal.__table__.columns["rehearsal_id"].primary_key)
        self.assertFalse(Rehearsal.__table__.columns["presentation_id"].nullable)
        self.assertTrue(Rehearsal.__table__.columns["presentation_id"].index)
        self.assertEqual(Rehearsal.__table__.columns["status"].type.length, 30)
        self.assertTrue(Rehearsal.__table__.columns["status"].index)
        self.assertTrue(Rehearsal.__table__.columns["deleted_at"].index)
        self.assertIn(
            "uq_rehearsals_presentation_id_attempt_number",
            {
                constraint.name
                for constraint in Rehearsal.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )

        self.assertTrue(RehearsalMedia.__table__.columns["media_id"].primary_key)
        self.assertEqual(RehearsalMedia.__table__.columns["media_type"].type.length, 20)
        self.assertEqual(RehearsalMedia.__table__.columns["original_filename"].type.length, 255)
        self.assertFalse(RehearsalMedia.__table__.columns["object_key"].nullable)
        self.assertTrue(RehearsalMedia.__table__.columns["status"].index)

    def test_audio_pose_gaze_and_slide_result_tables_match_specification(self) -> None:
        self.assertTrue(AudioAnalysis.__table__.columns["rehearsal_id"].unique)
        self.assertEqual(AudioAnalysis.__table__.columns["words_per_minute"].type.precision, 6)
        self.assertEqual(AudioAnalysis.__table__.columns["words_per_minute"].type.scale, 2)
        self.assertFalse(AudioAnalysis.__table__.columns["filler_word_count"].nullable)
        self.assertTrue(AudioAnalysis.__table__.columns["status"].index)

        self.assertEqual(FillerWordEvent.__table__.columns["filler_word"].type.length, 50)
        self.assertEqual(FillerWordEvent.__table__.columns["start_seconds"].type.scale, 3)
        self.assertEqual(FillerWordEvent.__table__.columns["confidence"].type.precision, 5)
        self.assertEqual(SpeechEvent.__table__.columns["event_type"].type.length, 50)
        self.assertTrue(SpeechEvent.__table__.columns["event_type"].index)

        self.assertTrue(PoseAnalysis.__table__.columns["rehearsal_id"].unique)
        self.assertEqual(PoseAnalysis.__table__.columns["posture_score"].type.precision, 5)
        self.assertFalse(PoseAnalysis.__table__.columns["movement_count"].nullable)
        self.assertEqual(PoseEvent.__table__.columns["event_type"].type.length, 50)

        self.assertTrue(GazeAnalysis.__table__.columns["rehearsal_id"].unique)
        self.assertEqual(GazeAnalysis.__table__.columns["professor_ratio"].type.scale, 2)
        self.assertEqual(GazeEvent.__table__.columns["target"].type.length, 50)
        self.assertTrue(GazeEvent.__table__.columns["target"].index)

        self.assertFalse(RehearsalSlideResult.__table__.columns["planned_seconds"].nullable)
        self.assertFalse(RehearsalSlideResult.__table__.columns["actual_seconds"].nullable)
        self.assertEqual(RehearsalSlideResult.__table__.columns["coverage_score"].type.precision, 5)
        self.assertIn(
            "uq_rehearsal_slide_results_rehearsal_id_slide_id",
            {
                constraint.name
                for constraint in RehearsalSlideResult.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )

    def test_postgresql_ddl_contains_identity_foreign_keys_and_jsonb(self) -> None:
        rehearsal_ddl = str(CreateTable(Rehearsal.__table__).compile(dialect=postgresql.dialect())).upper()
        audio_ddl = str(CreateTable(AudioAnalysis.__table__).compile(dialect=postgresql.dialect())).upper()
        pose_event_ddl = str(CreateTable(PoseEvent.__table__).compile(dialect=postgresql.dialect())).upper()
        slide_result_ddl = str(
            CreateTable(RehearsalSlideResult.__table__).compile(dialect=postgresql.dialect())
        ).upper()

        self.assertIn("REHEARSAL_ID BIGINT GENERATED ALWAYS AS IDENTITY", rehearsal_ddl)
        self.assertIn("FOREIGN KEY(PRESENTATION_ID) REFERENCES PRESENTATIONS", rehearsal_ddl)
        self.assertIn("OMISSION_SUMMARY JSONB", audio_ddl)
        self.assertIn("ADDITIONAL_CONTENT_SUMMARY JSONB", audio_ddl)
        self.assertIn("DETAILS JSONB", pose_event_ddl)
        self.assertIn("FOREIGN KEY(SLIDE_ID) REFERENCES SLIDES (SLIDE_ID) ON DELETE CASCADE", slide_result_ddl)

    def test_models_create_and_persist_full_rehearsal_analysis_graph(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        for table_name in (
            "rehearsals",
            "rehearsal_media",
            "audio_analyses",
            "filler_word_events",
            "speech_events",
            "pose_analyses",
            "pose_events",
            "gaze_analyses",
            "gaze_events",
            "rehearsal_slide_results",
        ):
            self.assertTrue(inspector.has_table(table_name))

        with Session(engine) as session:
            user = User(
                user_id=1,
                email="rehearsal@example.com",
                password_hash="hash",
                name="Presenter",
            )
            presentation = Presentation(
                presentation_id=1,
                user=user,
                title="AI Speech Demo",
                total_duration_seconds=600,
                qa_duration_seconds=120,
                presentation_duration_seconds=480,
            )
            file = PresentationFile(
                file_id=1,
                presentation=presentation,
                original_filename="demo.pdf",
                file_type="PDF",
                mime_type="application/pdf",
                file_size_bytes=1024,
                storage_bucket="local",
                object_key="presentations/1/demo.pdf",
                status="UPLOADED",
                slide_count=1,
            )
            slide = Slide(
                slide_id=1,
                presentation=presentation,
                file=file,
                slide_number=1,
                sort_order=1,
                title="Problem",
                raw_text="Problem statement",
            )
            rehearsal = Rehearsal(
                rehearsal_id=1,
                presentation=presentation,
                attempt_number=1,
                total_duration_seconds=470,
            )
            media = RehearsalMedia(
                media_id=1,
                rehearsal=rehearsal,
                media_type="AUDIO",
                original_filename="practice.m4a",
                mime_type="audio/mp4",
                file_size_bytes=2048,
                storage_bucket="local",
                object_key="rehearsals/1/practice.m4a",
                duration_seconds=Decimal("470.500"),
                status="UPLOADED",
            )
            audio = AudioAnalysis(
                audio_analysis_id=1,
                rehearsal=rehearsal,
                transcript_text="음, 프로젝트 문제를 설명합니다.",
                language="ko",
                duration_seconds=Decimal("470.500"),
                words_per_minute=Decimal("125.40"),
                filler_word_count=1,
                omission_summary={"missing": ["기대효과"]},
                status="COMPLETED",
            )
            filler = FillerWordEvent(
                filler_word_event_id=1,
                audio_analysis=audio,
                filler_word="음",
                start_seconds=Decimal("1.200"),
                end_seconds=Decimal("1.500"),
            )
            speech = SpeechEvent(
                speech_event_id=1,
                audio_analysis=audio,
                event_type="LONG_SILENCE",
                start_seconds=Decimal("22.000"),
                end_seconds=Decimal("25.500"),
                severity="MEDIUM",
            )
            pose = PoseAnalysis(
                pose_analysis_id=1,
                rehearsal=rehearsal,
                posture_score=Decimal("82.50"),
                stability_score=Decimal("78.00"),
                movement_count=2,
                raw_metrics={"shoulder_sway": 2},
                status="COMPLETED",
            )
            pose_event = PoseEvent(
                pose_event_id=1,
                pose_analysis=pose,
                event_type="BODY_SWAY",
                start_seconds=Decimal("40.000"),
                severity="LOW",
            )
            gaze = GazeAnalysis(
                gaze_analysis_id=1,
                rehearsal=rehearsal,
                professor_ratio=Decimal("60.00"),
                screen_ratio=Decimal("25.00"),
                floor_ratio=Decimal("10.00"),
                offscreen_ratio=Decimal("5.00"),
                dominant_target="PROFESSOR",
                status="COMPLETED",
            )
            gaze_event = GazeEvent(
                gaze_event_id=1,
                gaze_analysis=gaze,
                event_type="LONG_SCREEN_FIXATION",
                target="SCREEN",
                start_seconds=Decimal("80.000"),
                end_seconds=Decimal("95.000"),
            )
            slide_result = RehearsalSlideResult(
                rehearsal_slide_result_id=1,
                rehearsal=rehearsal,
                slide=slide,
                planned_seconds=90,
                actual_seconds=100,
                delta_seconds=10,
                coverage_score=Decimal("88.00"),
                omitted_keywords=["기대효과"],
            )

            session.add_all(
                [
                    user,
                    presentation,
                    file,
                    slide,
                    rehearsal,
                    media,
                    audio,
                    filler,
                    speech,
                    pose,
                    pose_event,
                    gaze,
                    gaze_event,
                    slide_result,
                ]
            )
            session.commit()
            session.refresh(rehearsal)

            self.assertEqual(rehearsal.status, RehearsalStatus.CREATED.value)
            self.assertEqual(presentation.rehearsals[0].media[0].media_type, "AUDIO")
            self.assertEqual(rehearsal.audio_analysis.filler_word_events[0].filler_word, "음")
            self.assertEqual(rehearsal.audio_analysis.speech_events[0].event_type, "LONG_SILENCE")
            self.assertEqual(rehearsal.pose_analysis.events[0].event_type, "BODY_SWAY")
            self.assertEqual(rehearsal.gaze_analysis.events[0].target, "SCREEN")
            self.assertEqual(rehearsal.slide_results[0].slide.title, "Problem")
            self.assertEqual(slide.rehearsal_results[0].actual_seconds, 100)


if __name__ == "__main__":
    unittest.main()
