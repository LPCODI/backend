import unittest
from decimal import Decimal

from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.db import Base
from app.domain import AgentType
from app.models import (
    AgentEvaluation,
    ComparisonMetric,
    EvaluationCriterion,
    EvaluationPriority,
    EvaluationPrioritySlide,
    FinalReport,
    Presentation,
    PresentationFile,
    QaAnswer,
    QaAnswerEvaluation,
    QaQuestion,
    QaQuestionSlide,
    QaSession,
    Rehearsal,
    RehearsalComparison,
    RehearsalMedia,
    ReportScore,
    Slide,
    User,
)


class EvaluationQaReportModelTest(unittest.TestCase):
    def test_agent_evaluation_tables_match_specification(self) -> None:
        self.assertEqual(AgentEvaluation.__tablename__, "agent_evaluations")
        self.assertTrue(AgentEvaluation.__table__.columns["evaluation_id"].primary_key)
        self.assertFalse(AgentEvaluation.__table__.columns["rehearsal_id"].nullable)
        self.assertTrue(AgentEvaluation.__table__.columns["rehearsal_id"].index)
        self.assertEqual(AgentEvaluation.__table__.columns["agent_type"].type.length, 30)
        self.assertTrue(AgentEvaluation.__table__.columns["agent_type"].index)
        self.assertEqual(AgentEvaluation.__table__.columns["total_score"].type.precision, 5)
        self.assertFalse(AgentEvaluation.__table__.columns["is_active"].nullable)
        self.assertIn(
            "uq_agent_evaluations_rehearsal_id_agent_type_version",
            {
                constraint.name
                for constraint in AgentEvaluation.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )

        self.assertEqual(EvaluationCriterion.__table__.columns["criterion_code"].type.length, 50)
        self.assertFalse(EvaluationCriterion.__table__.columns["score"].nullable)
        self.assertEqual(EvaluationPriority.__table__.columns["priority_rank"].type.python_type, int)
        self.assertFalse(EvaluationPriority.__table__.columns["reason"].nullable)
        self.assertIn(
            "pk_evaluation_priority_slides",
            {
                constraint.name
                for constraint in EvaluationPrioritySlide.__table__.constraints
                if isinstance(constraint, PrimaryKeyConstraint)
            },
        )

    def test_qa_report_and_comparison_tables_match_specification(self) -> None:
        self.assertEqual(QaSession.__table__.columns["status"].type.length, 30)
        self.assertTrue(QaSession.__table__.columns["status"].index)
        self.assertEqual(QaQuestion.__table__.columns["question_text"].type.python_type, str)
        self.assertFalse(QaQuestion.__table__.columns["question_order"].nullable)
        self.assertIn(
            "pk_qa_question_slides",
            {
                constraint.name
                for constraint in QaQuestionSlide.__table__.constraints
                if isinstance(constraint, PrimaryKeyConstraint)
            },
        )

        self.assertEqual(QaAnswer.__table__.columns["answer_type"].type.length, 20)
        self.assertEqual(QaAnswer.__table__.columns["answer_duration_seconds"].type.scale, 3)
        self.assertTrue(QaAnswerEvaluation.__table__.columns["answer_id"].unique)
        self.assertEqual(QaAnswerEvaluation.__table__.columns["technical_accuracy_score"].type.precision, 5)

        self.assertFalse(FinalReport.__table__.columns["include_qa"].nullable)
        self.assertFalse(FinalReport.__table__.columns["include_comparison"].nullable)
        self.assertTrue(FinalReport.__table__.columns["pdf_status"].index)
        self.assertEqual(ReportScore.__table__.columns["score_type"].type.length, 50)
        self.assertEqual(RehearsalComparison.__table__.columns["overall_improvement_rate"].type.precision, 7)
        self.assertEqual(ComparisonMetric.__table__.columns["before_value"].type.scale, 4)

    def test_postgresql_ddl_contains_identity_foreign_keys_and_jsonb(self) -> None:
        evaluation_ddl = str(CreateTable(AgentEvaluation.__table__).compile(dialect=postgresql.dialect())).upper()
        question_ddl = str(CreateTable(QaQuestion.__table__).compile(dialect=postgresql.dialect())).upper()
        report_ddl = str(CreateTable(FinalReport.__table__).compile(dialect=postgresql.dialect())).upper()
        comparison_ddl = str(CreateTable(RehearsalComparison.__table__).compile(dialect=postgresql.dialect())).upper()

        self.assertIn("EVALUATION_ID BIGINT GENERATED ALWAYS AS IDENTITY", evaluation_ddl)
        self.assertIn("FOREIGN KEY(REHEARSAL_ID) REFERENCES REHEARSALS", evaluation_ddl)
        self.assertIn("STRENGTHS JSONB", evaluation_ddl)
        self.assertIn("ANSWER_KEYWORDS JSONB", question_ddl)
        self.assertIn("TOP_PRIORITIES JSONB", report_ddl)
        self.assertIn("FOREIGN KEY(BASE_REHEARSAL_ID) REFERENCES REHEARSALS", comparison_ddl)
        self.assertIn("FOREIGN KEY(TARGET_REHEARSAL_ID) REFERENCES REHEARSALS", comparison_ddl)

    def test_models_create_and_persist_evaluation_qa_report_graph(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        for table_name in (
            "agent_evaluations",
            "evaluation_criteria",
            "evaluation_priorities",
            "evaluation_priority_slides",
            "qa_sessions",
            "qa_questions",
            "qa_question_slides",
            "qa_answers",
            "qa_answer_evaluations",
            "final_reports",
            "report_scores",
            "rehearsal_comparisons",
            "comparison_metrics",
        ):
            self.assertTrue(inspector.has_table(table_name))

        with Session(engine) as session:
            user = User(user_id=1, email="eval@example.com", password_hash="hash", name="Presenter")
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
                title="Architecture",
                raw_text="System architecture",
            )
            base_rehearsal = Rehearsal(rehearsal_id=1, presentation=presentation, attempt_number=1)
            target_rehearsal = Rehearsal(rehearsal_id=2, presentation=presentation, attempt_number=2)
            media = RehearsalMedia(
                media_id=1,
                rehearsal=target_rehearsal,
                media_type="AUDIO",
                original_filename="answer.m4a",
                mime_type="audio/mp4",
                file_size_bytes=1024,
                storage_bucket="local",
                object_key="rehearsals/2/answer.m4a",
                status="UPLOADED",
            )
            evaluation = AgentEvaluation(
                evaluation_id=1,
                rehearsal=target_rehearsal,
                agent_type=AgentType.FINAL_JUDGE,
                version=1,
                total_score=Decimal("82.50"),
                strengths=["clear opening"],
                weaknesses=["needs evidence"],
                likely_questions=["기술 선택 이유는 무엇인가요?"],
                status="COMPLETED",
            )
            criterion = EvaluationCriterion(
                evaluation_criterion_id=1,
                evaluation=evaluation,
                criterion_code="CONTENT",
                criterion_name="내용 완성도",
                score=Decimal("80.00"),
            )
            priority = EvaluationPriority(
                priority_id=1,
                evaluation=evaluation,
                priority_rank=1,
                category="CONTENT",
                title="기술 선택 이유 보강",
                reason="교수 관점에서 근거가 부족합니다.",
                action="대안 비교를 한 문장 추가합니다.",
            )
            priority_slide = EvaluationPrioritySlide(priority=priority, slide=slide)
            qa_session = QaSession(qa_session_id=1, rehearsal=target_rehearsal, status="CREATED", question_count=1)
            question = QaQuestion(
                question_id=1,
                qa_session=qa_session,
                question_order=1,
                category="TECHNICAL_REASONING",
                difficulty="MEDIUM",
                question_text="왜 이 구조를 선택했나요?",
                answer_keywords=["성능", "유지보수"],
            )
            question_slide = QaQuestionSlide(question=question, slide=slide)
            answer = QaAnswer(
                answer_id=1,
                question=question,
                media=media,
                answer_type="AUDIO",
                answer_text="성능과 유지보수를 고려했습니다.",
                answer_duration_seconds=Decimal("12.500"),
                status="SUBMITTED",
            )
            answer_evaluation = QaAnswerEvaluation(
                answer_evaluation_id=1,
                answer=answer,
                total_score=Decimal("78.00"),
                technical_accuracy_score=Decimal("80.00"),
                recommended_answer="성능과 유지보수 trade-off를 근거로 설명합니다.",
            )
            report = FinalReport(
                report_id=1,
                rehearsal=target_rehearsal,
                version=1,
                summary="전체적으로 명확하지만 근거 보강이 필요합니다.",
                top_priorities=["기술 선택 이유 보강"],
                overall_score=Decimal("82.50"),
                pdf_status="PENDING",
            )
            report_score = ReportScore(
                report_score_id=1,
                report=report,
                score_type="CONTENT",
                score=Decimal("80.00"),
            )
            comparison = RehearsalComparison(
                comparison_id=1,
                presentation=presentation,
                base_rehearsal=base_rehearsal,
                target_rehearsal=target_rehearsal,
                overall_improvement_rate=Decimal("12.50"),
            )
            metric = ComparisonMetric(
                comparison_metric_id=1,
                comparison=comparison,
                metric_code="FILLER_WORDS",
                metric_name="추임새",
                before_value=Decimal("8.0000"),
                after_value=Decimal("3.0000"),
                change_value=Decimal("-5.0000"),
                improvement_rate=Decimal("62.50"),
                improved=True,
            )

            session.add_all(
                [
                    user,
                    presentation,
                    file,
                    slide,
                    base_rehearsal,
                    target_rehearsal,
                    media,
                    evaluation,
                    criterion,
                    priority,
                    priority_slide,
                    qa_session,
                    question,
                    question_slide,
                    answer,
                    answer_evaluation,
                    report,
                    report_score,
                    comparison,
                    metric,
                ]
            )
            session.commit()

            stored = session.get(Rehearsal, 2)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.agent_evaluations[0].criteria[0].criterion_code, "CONTENT")
            self.assertEqual(stored.qa_sessions[0].questions[0].answers[0].evaluation.total_score, Decimal("78.00"))
            self.assertEqual(stored.final_reports[0].scores[0].score, Decimal("80.00"))
            self.assertEqual(stored.target_comparisons[0].metrics[0].metric_code, "FILLER_WORDS")
            self.assertEqual(slide.evaluation_priority_links[0].priority.title, "기술 선택 이유 보강")
            self.assertEqual(slide.qa_question_links[0].question.question_text, "왜 이 구조를 선택했나요?")


if __name__ == "__main__":
    unittest.main()
