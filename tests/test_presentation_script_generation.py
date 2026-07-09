import unittest
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import ApiError
from app.db import Base
from app.domain import ErrorCode
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
from app.services import (
    SCRIPT_GENERATION_MODEL_NAME,
    SCRIPT_GENERATION_TYPE_AI,
    SCRIPT_GENERATION_TYPE_USER_EDIT,
    generate_presentation_script_drafts,
    generate_slide_script_drafts,
    create_user_edited_slide_script,
    get_latest_presentation_scripts,
    persist_presentation_script_drafts,
)


class PresentationScriptGenerationTest(unittest.TestCase):
    def _presentation(self) -> Presentation:
        return Presentation(
            presentation_id=1,
            user_id=1,
            title="AI Speech Backend",
            total_duration_seconds=600,
            qa_duration_seconds=120,
            presentation_duration_seconds=480,
        )

    def _slide(self, slide_id: int, slide_number: int, sort_order: int, title: str, *, excluded: bool = False) -> Slide:
        return Slide(
            slide_id=slide_id,
            presentation_id=1,
            file_id=1,
            slide_number=slide_number,
            sort_order=sort_order,
            title=title,
            raw_text="FastAPI 서버가 발표 자료 분석과 리허설 피드백 흐름을 관리합니다.",
            notes_text="교수님께 구조와 책임 분리를 중심으로 설명합니다.",
            excluded=excluded,
        )

    def test_generate_slide_script_drafts_reflects_analysis_timing_and_transitions(self) -> None:
        presentation = self._presentation()
        first = self._slide(10, 1, 1, "Problem")
        excluded = self._slide(11, 2, 2, "Appendix", excluded=True)
        second = self._slide(12, 3, 3, "Architecture")
        timing = SlideTiming(
            slide_timing_id=1,
            slide_id=first.slide_id,
            version=1,
            allocated_seconds=150,
            transition_seconds=5,
        )
        analysis = SlideAnalysis(
            slide_analysis_id=1,
            presentation_analysis_id=1,
            slide_id=first.slide_id,
            importance_score=Decimal("4.50"),
            complexity_score=Decimal("3.20"),
            core_message="문제 정의와 백엔드 책임을 먼저 분명히 전달해야 합니다.",
            keywords=["FastAPI", "분석", "피드백"],
            missing_explanations=["장애 대응 흐름 설명이 부족합니다."],
            expected_questions=[
                {
                    "question": "FastAPI를 선택한 이유는 무엇인가요?",
                    "reason": "기술 선택 근거를 확인할 수 있습니다.",
                }
            ],
        )

        drafts = generate_slide_script_drafts(
            presentation=presentation,
            slides=[second, excluded, first],
            timings_by_slide_id={first.slide_id: timing},
            analyses_by_slide_id={first.slide_id: analysis},
        )

        self.assertEqual([draft.slide_id for draft in drafts], [first.slide_id, second.slide_id])
        self.assertEqual(drafts[0].estimated_seconds, 150)
        self.assertEqual(drafts[0].emphasis_words, ("FastAPI", "분석", "피드백"))
        self.assertIn("문제 정의와 백엔드 책임", drafts[0].script_text)
        self.assertIn("Architecture", drafts[0].transition_sentence)
        self.assertEqual(drafts[0].optional_explanation, "장애 대응 흐름 설명이 부족합니다.")
        self.assertEqual(drafts[0].expected_questions[0]["question"], "FastAPI를 선택한 이유는 무엇인가요?")
        self.assertEqual(drafts[0].generation_type, SCRIPT_GENERATION_TYPE_AI)
        self.assertEqual(drafts[0].model_name, SCRIPT_GENERATION_MODEL_NAME)
        self.assertNotIn("Appendix", "\n".join(draft.script_text for draft in drafts))

    def test_generate_slide_script_drafts_rejects_empty_active_slide_set(self) -> None:
        with self.assertRaises(ApiError) as raised:
            generate_slide_script_drafts(
                presentation=self._presentation(),
                slides=[self._slide(11, 2, 2, "Appendix", excluded=True)],
            )

        self.assertEqual(raised.exception.code, ErrorCode.SCRIPT_NOT_READY)


class PresentationScriptGenerationPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                Presentation.__table__,
                PresentationFile.__table__,
                Slide.__table__,
                PresentationAnalysis.__table__,
                SlideAnalysis.__table__,
                SlideTiming.__table__,
                SlideScript.__table__,
            ],
        )

    def tearDown(self) -> None:
        Base.metadata.drop_all(
            self.engine,
            tables=[
                SlideTiming.__table__,
                SlideScript.__table__,
                SlideAnalysis.__table__,
                PresentationAnalysis.__table__,
                Slide.__table__,
                PresentationFile.__table__,
                Presentation.__table__,
                User.__table__,
            ],
        )
        self.engine.dispose()

    def test_generate_presentation_script_drafts_loads_owned_project_context(self) -> None:
        with self.session_factory() as session:
            user = User(user_id=1, email="script@example.com", password_hash="hash", name="Script Owner")
            presentation = Presentation(
                presentation_id=1,
                user_id=user.user_id,
                title="Script Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
                presentation_duration_seconds=480,
            )
            file = PresentationFile(
                file_id=1,
                presentation_id=presentation.presentation_id,
                original_filename="script.pdf",
                stored_filename="script.pdf",
                file_type="PDF",
                mime_type="application/pdf",
                file_size_bytes=128,
                storage_bucket="local",
                object_key="presentations/1/script.pdf",
                status="PARSED",
            )
            slide = Slide(
                slide_id=1,
                presentation_id=presentation.presentation_id,
                file_id=file.file_id,
                slide_number=1,
                sort_order=1,
                title="Architecture",
                raw_text="백엔드가 문서 분석, 시간 배분, 대본 생성을 연결합니다.",
                notes_text="교수님께 책임 분리를 강조합니다.",
            )
            analysis = PresentationAnalysis(
                presentation_analysis_id=1,
                presentation_id=presentation.presentation_id,
                version=1,
                status="COMPLETED",
            )
            slide_analysis = SlideAnalysis(
                slide_analysis_id=1,
                presentation_analysis_id=analysis.presentation_analysis_id,
                slide_id=slide.slide_id,
                core_message="백엔드 책임 분리를 중심으로 설명해야 합니다.",
                keywords=["문서 분석", "시간 배분", "대본 생성"],
            )
            timing = SlideTiming(
                slide_timing_id=1,
                slide_id=slide.slide_id,
                version=1,
                allocated_seconds=180,
                transition_seconds=0,
                is_active=True,
            )
            session.add_all([user, presentation, file, slide, analysis, slide_analysis, timing])
            session.commit()

            result = generate_presentation_script_drafts(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
            )

        self.assertEqual(result.presentation.presentation_id, 1)
        self.assertEqual(len(result.scripts), 1)
        self.assertEqual(result.scripts[0].estimated_seconds, 180)
        self.assertIn("백엔드 책임 분리", result.scripts[0].core_message)

    def test_persist_scripts_and_user_edits_keep_version_history(self) -> None:
        with self.session_factory() as session:
            user = User(user_id=1, email="history@example.com", password_hash="hash", name="History Owner")
            presentation = Presentation(
                presentation_id=1,
                user_id=user.user_id,
                title="Script History Project",
                total_duration_seconds=600,
                qa_duration_seconds=120,
                presentation_duration_seconds=480,
            )
            file = PresentationFile(
                file_id=1,
                presentation_id=presentation.presentation_id,
                original_filename="history.pdf",
                stored_filename="history.pdf",
                file_type="PDF",
                mime_type="application/pdf",
                file_size_bytes=128,
                storage_bucket="local",
                object_key="presentations/1/history.pdf",
                status="PARSED",
            )
            slide = Slide(
                slide_id=1,
                presentation_id=presentation.presentation_id,
                file_id=file.file_id,
                slide_number=1,
                sort_order=1,
                title="Problem",
                raw_text="기존 발표 연습은 리허설 피드백이 부족합니다.",
            )
            timing = SlideTiming(
                slide_timing_id=1,
                slide_id=slide.slide_id,
                version=1,
                allocated_seconds=120,
                transition_seconds=0,
                is_active=True,
            )
            session.add_all([user, presentation, file, slide, timing])
            session.commit()

            generated = persist_presentation_script_drafts(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
            )
            edited = create_user_edited_slide_script(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
                slide_id=slide.slide_id,
                script_text="교수님, 기존 발표 연습의 한계와 저희 프로젝트의 보완 지점을 설명드리겠습니다.",
                user_revision_note="도입 문장을 더 직접적으로 수정했습니다.",
            )
            latest = get_latest_presentation_scripts(
                session,
                user=user,
                presentation_id=presentation.presentation_id,
            )

            all_scripts = session.execute(select(SlideScript).order_by(SlideScript.version)).scalars().all()

        self.assertEqual(generated.presentation.script_status, "COMPLETED")
        self.assertEqual(len(generated.scripts), 1)
        self.assertEqual(generated.scripts[0].version, 1)
        self.assertEqual(generated.scripts[0].generation_type, SCRIPT_GENERATION_TYPE_AI)
        self.assertEqual(edited.version, 2)
        self.assertEqual(edited.previous_slide_script_id, generated.scripts[0].slide_script_id)
        self.assertEqual(edited.edited_by_user_id, user.user_id)
        self.assertEqual(edited.generation_type, SCRIPT_GENERATION_TYPE_USER_EDIT)
        self.assertEqual(edited.user_revision_note, "도입 문장을 더 직접적으로 수정했습니다.")
        self.assertEqual([script.is_active for script in all_scripts], [False, True])
        self.assertEqual(latest.scripts[0].slide_script_id, edited.slide_script_id)


if __name__ == "__main__":
    unittest.main()
