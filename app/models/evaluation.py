"""Agent evaluation, Q&A, final report, and rehearsal comparison models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.domain import AgentType

if TYPE_CHECKING:
    from app.models.presentation import Presentation, Slide
    from app.models.rehearsal import Rehearsal, RehearsalMedia

JsonObject = dict[str, Any] | list[Any]
JSONB = JSON().with_variant(postgresql.JSONB, "postgresql")


class AgentEvaluation(Base):
    """Versioned professor, student, or final-judge evaluation for a rehearsal."""

    __tablename__ = "agent_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "rehearsal_id",
            "agent_type",
            "version",
            name="uq_agent_evaluations_rehearsal_id_agent_type_version",
        ),
        Index("ix_agent_evaluations_rehearsal_id_agent_type_status", "rehearsal_id", "agent_type", "status"),
    )

    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[AgentType] = mapped_column(String(30), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    likely_questions: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    confusing_sections: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="agent_evaluations")
    criteria: Mapped[list["EvaluationCriterion"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    priorities: Mapped[list["EvaluationPriority"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EvaluationCriterion(Base):
    """Score and feedback for one criterion in an agent evaluation."""

    __tablename__ = "evaluation_criteria"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "criterion_code",
            name="uq_evaluation_criteria_evaluation_id_criterion_code",
        ),
    )

    evaluation_criterion_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_evaluations.evaluation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    criterion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation: Mapped["AgentEvaluation"] = relationship(back_populates="criteria")


class EvaluationPriority(Base):
    """Final-judge improvement priority and its recommended action."""

    __tablename__ = "evaluation_priorities"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "priority_rank", name="uq_evaluation_priorities_evaluation_id_priority_rank"),
    )

    priority_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_evaluations.evaluation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation: Mapped["AgentEvaluation"] = relationship(back_populates="priorities")
    slide_links: Mapped[list["EvaluationPrioritySlide"]] = relationship(
        back_populates="priority",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EvaluationPrioritySlide(Base):
    """Association between an improvement priority and related slides."""

    __tablename__ = "evaluation_priority_slides"
    __table_args__ = (
        PrimaryKeyConstraint("priority_id", "slide_id", name="pk_evaluation_priority_slides"),
    )

    priority_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("evaluation_priorities.priority_id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    priority: Mapped["EvaluationPriority"] = relationship(back_populates="slide_links")
    slide: Mapped["Slide"] = relationship(back_populates="evaluation_priority_links")


class QaSession(Base):
    """Question-and-answer practice session for one rehearsal."""

    __tablename__ = "qa_sessions"

    qa_session_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="qa_sessions")
    questions: Mapped[list["QaQuestion"]] = relationship(
        back_populates="qa_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QaQuestion(Base):
    """Professor-style expected question and answer guidance."""

    __tablename__ = "qa_questions"
    __table_args__ = (
        UniqueConstraint("qa_session_id", "question_order", name="uq_qa_questions_qa_session_id_question_order"),
    )

    question_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    qa_session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("qa_sessions.qa_session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_keywords: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    qa_session: Mapped["QaSession"] = relationship(back_populates="questions")
    slide_links: Mapped[list["QaQuestionSlide"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    answers: Mapped[list["QaAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QaQuestionSlide(Base):
    """Association between an expected question and related slides."""

    __tablename__ = "qa_question_slides"
    __table_args__ = (
        PrimaryKeyConstraint("question_id", "slide_id", name="pk_qa_question_slides"),
    )

    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("qa_questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped["QaQuestion"] = relationship(back_populates="slide_links")
    slide: Mapped["Slide"] = relationship(back_populates="qa_question_links")


class QaAnswer(Base):
    """Submitted text or audio answer to a Q&A question."""

    __tablename__ = "qa_answers"

    answer_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("qa_questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("rehearsal_media.media_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    answer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    question: Mapped["QaQuestion"] = relationship(back_populates="answers")
    media: Mapped["RehearsalMedia | None"] = relationship(back_populates="qa_answers")
    evaluation: Mapped["QaAnswerEvaluation | None"] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QaAnswerEvaluation(Base):
    """Detailed score and recommended answer for a submitted Q&A answer."""

    __tablename__ = "qa_answer_evaluations"

    answer_evaluation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    answer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("qa_answers.answer_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    intent_understanding_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    conclusion_first_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    specificity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    logic_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    conciseness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    strengths: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    recommended_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    answer: Mapped["QaAnswer"] = relationship(back_populates="evaluation")


class FinalReport(Base):
    """Versioned rehearsal report and PDF generation state."""

    __tablename__ = "final_reports"
    __table_args__ = (
        UniqueConstraint("rehearsal_id", "version", name="uq_final_reports_rehearsal_id_version"),
        Index("ix_final_reports_rehearsal_id_is_latest", "rehearsal_id", "is_latest"),
    )

    report_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_priorities: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    include_qa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    include_comparison: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    pdf_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    pdf_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="final_reports")
    scores: Mapped[list["ReportScore"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReportScore(Base):
    """Score for one report area such as delivery, content, or Q&A."""

    __tablename__ = "report_scores"
    __table_args__ = (
        UniqueConstraint("report_id", "score_type", name="uq_report_scores_report_id_score_type"),
    )

    report_score_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("final_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    report: Mapped["FinalReport"] = relationship(back_populates="scores")


class RehearsalComparison(Base):
    """Comparison between two rehearsals in the same presentation."""

    __tablename__ = "rehearsal_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "presentation_id",
            "base_rehearsal_id",
            "target_rehearsal_id",
            name="uq_rehearsal_comparisons_pair",
        ),
    )

    comparison_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    presentation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_improvement_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    presentation: Mapped["Presentation"] = relationship(back_populates="rehearsal_comparisons")
    base_rehearsal: Mapped["Rehearsal"] = relationship(
        foreign_keys=[base_rehearsal_id],
        back_populates="base_comparisons",
    )
    target_rehearsal: Mapped["Rehearsal"] = relationship(
        foreign_keys=[target_rehearsal_id],
        back_populates="target_comparisons",
    )
    metrics: Mapped[list["ComparisonMetric"]] = relationship(
        back_populates="comparison",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ComparisonMetric(Base):
    """Metric-level before/after values for a rehearsal comparison."""

    __tablename__ = "comparison_metrics"
    __table_args__ = (
        UniqueConstraint("comparison_id", "metric_code", name="uq_comparison_metrics_comparison_id_metric_code"),
    )

    comparison_metric_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    comparison_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsal_comparisons.comparison_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    before_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    after_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    change_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    improvement_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    improved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    comparison: Mapped["RehearsalComparison"] = relationship(back_populates="metrics")
