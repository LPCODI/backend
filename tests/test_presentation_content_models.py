import unittest
from decimal import Decimal

from sqlalchemy import UniqueConstraint, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db import Base
from app.domain import DEFAULT_PRESENTATION_CONTEXT, PresentationStatus
from app.models import (
    Presentation,
    PresentationAnalysis,
    PresentationFile,
    Slide,
    SlideAnalysis,
    SlideScript,
    SlideTiming,
    User,
)


class PresentationContentModelTest(unittest.TestCase):
    def test_presentation_table_matches_project_specification(self) -> None:
        columns = Presentation.__table__.columns

        self.assertEqual(Presentation.__tablename__, "presentations")
        self.assertIn("presentation_id", columns)
        self.assertNotIn("id", columns)
        self.assertTrue(columns["presentation_id"].primary_key)
        self.assertFalse(columns["user_id"].nullable)
        self.assertTrue(columns["user_id"].index)
        self.assertEqual(columns["title"].type.length, 200)
        self.assertFalse(columns["total_duration_seconds"].nullable)
        self.assertFalse(columns["qa_duration_seconds"].nullable)
        self.assertFalse(columns["presentation_duration_seconds"].nullable)
        self.assertEqual(columns["presentation_context"].type.length, 50)
        self.assertEqual(columns["status"].type.length, 40)
        self.assertEqual(columns["timing_status"].type.length, 30)
        self.assertEqual(columns["script_status"].type.length, 30)
        self.assertTrue(columns["duplicated_from_id"].nullable)
        self.assertTrue(columns["deleted_at"].index)

    def test_file_slide_analysis_timing_and_script_tables_match_specification(self) -> None:
        self.assertEqual(PresentationFile.__table__.columns["file_id"].primary_key, True)
        self.assertEqual(PresentationFile.__table__.columns["original_filename"].type.length, 255)
        self.assertEqual(PresentationFile.__table__.columns["file_type"].type.length, 20)
        self.assertEqual(PresentationFile.__table__.columns["mime_type"].type.length, 100)
        self.assertFalse(PresentationFile.__table__.columns["file_size_bytes"].nullable)
        self.assertFalse(PresentationFile.__table__.columns["storage_bucket"].nullable)
        self.assertFalse(PresentationFile.__table__.columns["object_key"].nullable)
        self.assertTrue(PresentationFile.__table__.columns["status"].index)

        slide_columns = Slide.__table__.columns
        self.assertEqual(slide_columns["slide_id"].primary_key, True)
        self.assertEqual(slide_columns["title"].type.length, 300)
        self.assertFalse(slide_columns["slide_number"].nullable)
        self.assertFalse(slide_columns["sort_order"].nullable)
        self.assertFalse(slide_columns["excluded"].nullable)
        self.assertIn(
            "uq_slides_presentation_id_sort_order",
            {
                constraint.name
                for constraint in Slide.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )

        self.assertEqual(PresentationAnalysis.__table__.columns["version"].nullable, False)
        self.assertEqual(PresentationAnalysis.__table__.columns["model_name"].type.length, 100)
        self.assertEqual(SlideAnalysis.__table__.columns["importance_score"].type.precision, 5)
        self.assertEqual(SlideAnalysis.__table__.columns["importance_score"].type.scale, 2)
        self.assertFalse(SlideTiming.__table__.columns["allocated_seconds"].nullable)
        self.assertFalse(SlideTiming.__table__.columns["transition_seconds"].nullable)
        self.assertFalse(SlideTiming.__table__.columns["is_locked"].nullable)
        self.assertFalse(SlideScript.__table__.columns["script_text"].nullable)
        self.assertTrue(SlideScript.__table__.columns["previous_slide_script_id"].nullable)
        self.assertTrue(SlideScript.__table__.columns["edited_by_user_id"].nullable)
        self.assertTrue(SlideScript.__table__.columns["revision_reason"].nullable)
        self.assertTrue(SlideScript.__table__.columns["user_revision_note"].nullable)
        self.assertEqual(SlideScript.__table__.columns["generation_type"].type.length, 30)
        self.assertFalse(SlideScript.__table__.columns["is_active"].nullable)

    def test_postgresql_ddl_contains_identity_foreign_keys_and_jsonb(self) -> None:
        presentation_ddl = str(CreateTable(Presentation.__table__).compile(dialect=postgresql.dialect())).upper()
        analysis_ddl = str(CreateTable(PresentationAnalysis.__table__).compile(dialect=postgresql.dialect())).upper()
        slide_script_ddl = str(CreateTable(SlideScript.__table__).compile(dialect=postgresql.dialect())).upper()

        self.assertIn("PRESENTATION_ID BIGINT GENERATED ALWAYS AS IDENTITY", presentation_ddl)
        self.assertIn("CONSTRAINT PK_PRESENTATIONS PRIMARY KEY (PRESENTATION_ID)", presentation_ddl)
        self.assertIn("FOREIGN KEY(USER_ID) REFERENCES USERS (USER_ID) ON DELETE CASCADE", presentation_ddl)
        self.assertIn("STRENGTHS JSONB", analysis_ddl)
        self.assertIn("PROFESSOR_QUESTION_POINTS JSONB", analysis_ddl)
        self.assertIn("EMPHASIS_WORDS JSONB", slide_script_ddl)
        self.assertIn("FOREIGN KEY(SLIDE_ID) REFERENCES SLIDES (SLIDE_ID) ON DELETE CASCADE", slide_script_ddl)

    def test_models_create_and_persist_full_presentation_content_graph(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        for table_name in (
            "presentations",
            "presentation_files",
            "slides",
            "presentation_analyses",
            "slide_analyses",
            "slide_timings",
            "slide_scripts",
        ):
            self.assertTrue(inspector.has_table(table_name))

        with Session(engine) as session:
            user = User(
                user_id=1,
                email="presenter@example.com",
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
            analysis = PresentationAnalysis(
                presentation_analysis_id=1,
                presentation=presentation,
                version=1,
                summary="Summary",
                strengths=["clear flow"],
                professor_question_points=[{"slide": 1, "question": "Why this approach?"}],
                status="COMPLETED",
            )
            slide_analysis = SlideAnalysis(
                slide_analysis_id=1,
                presentation_analysis=analysis,
                slide=slide,
                importance_score=Decimal("4.50"),
                complexity_score=Decimal("3.25"),
                keywords=["problem", "solution"],
            )
            timing = SlideTiming(
                slide_timing_id=1,
                slide=slide,
                version=1,
                allocated_seconds=90,
                transition_seconds=5,
            )
            script = SlideScript(
                slide_script_id=1,
                slide=slide,
                version=1,
                script_text="교수님께 프로젝트 문제 정의를 설명합니다.",
                generation_type="AI",
                revision_reason="초기 대본 생성",
                emphasis_words=["문제 정의"],
            )
            edited_script = SlideScript(
                slide_script_id=2,
                slide=slide,
                previous_script=script,
                edited_by_user=user,
                version=2,
                script_text="교수님께 프로젝트 문제 정의와 핵심 가설을 설명합니다.",
                generation_type="USER_EDIT",
                revision_reason="사용자 직접 수정",
                user_revision_note="핵심 가설을 보강했습니다.",
            )
            session.add_all([user, presentation, file, slide, analysis, slide_analysis, timing, script, edited_script])
            session.commit()
            session.refresh(presentation)

            self.assertEqual(presentation.presentation_context, DEFAULT_PRESENTATION_CONTEXT.value)
            self.assertEqual(presentation.status, PresentationStatus.DRAFT.value)
            self.assertEqual(len(user.presentations), 1)
            self.assertEqual(presentation.files[0].slides[0].title, "Problem")
            self.assertEqual(presentation.slides[0].timings[0].allocated_seconds, 90)
            self.assertEqual(presentation.slides[0].scripts[0].generation_type, "AI")
            self.assertEqual(presentation.slides[0].scripts[1].previous_script.slide_script_id, 1)
            self.assertEqual(presentation.slides[0].scripts[1].edited_by_user.email, "presenter@example.com")
            self.assertEqual(presentation.analyses[0].slide_analyses[0].keywords, ["problem", "solution"])


if __name__ == "__main__":
    unittest.main()
