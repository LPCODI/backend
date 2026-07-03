"""Add evaluation, Q&A, report, and comparison tables.

Revision ID: 20260703_0005
Revises: 20260703_0004
Create Date: 2026-07-03 00:00:04.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0005"
down_revision: str | None = "20260703_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create agent evaluation, Q&A, report, and comparison tables."""

    op.create_table(
        "agent_evaluations",
        sa.Column("evaluation_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_type", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("strengths", jsonb, nullable=True),
        sa.Column("weaknesses", jsonb, nullable=True),
        sa.Column("likely_questions", jsonb, nullable=True),
        sa.Column("confusing_sections", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_agent_evaluations_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evaluation_id", name=op.f("pk_agent_evaluations")),
        sa.UniqueConstraint(
            "rehearsal_id",
            "agent_type",
            "version",
            name=op.f("uq_agent_evaluations_rehearsal_id_agent_type_version"),
        ),
    )
    op.create_index(op.f("ix_agent_evaluations_agent_type"), "agent_evaluations", ["agent_type"], unique=False)
    op.create_index(op.f("ix_agent_evaluations_rehearsal_id"), "agent_evaluations", ["rehearsal_id"], unique=False)
    op.create_index(op.f("ix_agent_evaluations_status"), "agent_evaluations", ["status"], unique=False)

    op.create_table(
        "evaluation_criteria",
        sa.Column("evaluation_criterion_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("evaluation_id", sa.BigInteger(), nullable=False),
        sa.Column("criterion_code", sa.String(length=50), nullable=False),
        sa.Column("criterion_name", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["agent_evaluations.evaluation_id"],
            name=op.f("fk_evaluation_criteria_evaluation_id_agent_evaluations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evaluation_criterion_id", name=op.f("pk_evaluation_criteria")),
        sa.UniqueConstraint(
            "evaluation_id",
            "criterion_code",
            name=op.f("uq_evaluation_criteria_evaluation_id_criterion_code"),
        ),
    )
    op.create_index(
        op.f("ix_evaluation_criteria_criterion_code"),
        "evaluation_criteria",
        ["criterion_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_criteria_evaluation_id"),
        "evaluation_criteria",
        ["evaluation_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_priorities",
        sa.Column("priority_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("evaluation_id", sa.BigInteger(), nullable=False),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["agent_evaluations.evaluation_id"],
            name=op.f("fk_evaluation_priorities_evaluation_id_agent_evaluations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("priority_id", name=op.f("pk_evaluation_priorities")),
        sa.UniqueConstraint(
            "evaluation_id",
            "priority_rank",
            name=op.f("uq_evaluation_priorities_evaluation_id_priority_rank"),
        ),
    )
    op.create_index(op.f("ix_evaluation_priorities_category"), "evaluation_priorities", ["category"], unique=False)
    op.create_index(
        op.f("ix_evaluation_priorities_evaluation_id"),
        "evaluation_priorities",
        ["evaluation_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_priority_slides",
        sa.Column("priority_id", sa.BigInteger(), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["priority_id"],
            ["evaluation_priorities.priority_id"],
            name=op.f("fk_evaluation_priority_slides_priority_id_evaluation_priorities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_evaluation_priority_slides_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("priority_id", "slide_id", name=op.f("pk_evaluation_priority_slides")),
    )
    op.create_index(
        op.f("ix_evaluation_priority_slides_slide_id"),
        "evaluation_priority_slides",
        ["slide_id"],
        unique=False,
    )

    op.create_table(
        "qa_sessions",
        sa.Column("qa_session_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_qa_sessions_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("qa_session_id", name=op.f("pk_qa_sessions")),
    )
    op.create_index(op.f("ix_qa_sessions_rehearsal_id"), "qa_sessions", ["rehearsal_id"], unique=False)
    op.create_index(op.f("ix_qa_sessions_status"), "qa_sessions", ["status"], unique=False)

    op.create_table(
        "qa_questions",
        sa.Column("question_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("qa_session_id", sa.BigInteger(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("answer_keywords", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["qa_session_id"],
            ["qa_sessions.qa_session_id"],
            name=op.f("fk_qa_questions_qa_session_id_qa_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_id", name=op.f("pk_qa_questions")),
        sa.UniqueConstraint(
            "qa_session_id",
            "question_order",
            name=op.f("uq_qa_questions_qa_session_id_question_order"),
        ),
    )
    op.create_index(op.f("ix_qa_questions_category"), "qa_questions", ["category"], unique=False)
    op.create_index(op.f("ix_qa_questions_qa_session_id"), "qa_questions", ["qa_session_id"], unique=False)

    op.create_table(
        "qa_question_slides",
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["qa_questions.question_id"],
            name=op.f("fk_qa_question_slides_question_id_qa_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_qa_question_slides_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_id", "slide_id", name=op.f("pk_qa_question_slides")),
    )
    op.create_index(op.f("ix_qa_question_slides_slide_id"), "qa_question_slides", ["slide_id"], unique=False)

    op.create_table(
        "qa_answers",
        sa.Column("answer_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("media_id", sa.BigInteger(), nullable=True),
        sa.Column("answer_type", sa.String(length=20), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_duration_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["rehearsal_media.media_id"],
            name=op.f("fk_qa_answers_media_id_rehearsal_media"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["qa_questions.question_id"],
            name=op.f("fk_qa_answers_question_id_qa_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("answer_id", name=op.f("pk_qa_answers")),
    )
    op.create_index(op.f("ix_qa_answers_media_id"), "qa_answers", ["media_id"], unique=False)
    op.create_index(op.f("ix_qa_answers_question_id"), "qa_answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_qa_answers_status"), "qa_answers", ["status"], unique=False)

    op.create_table(
        "qa_answer_evaluations",
        sa.Column("answer_evaluation_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("answer_id", sa.BigInteger(), nullable=False),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("intent_understanding_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("conclusion_first_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("specificity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("logic_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("technical_accuracy_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("conciseness_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("strengths", jsonb, nullable=True),
        sa.Column("weaknesses", jsonb, nullable=True),
        sa.Column("recommended_answer", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["qa_answers.answer_id"],
            name=op.f("fk_qa_answer_evaluations_answer_id_qa_answers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("answer_evaluation_id", name=op.f("pk_qa_answer_evaluations")),
        sa.UniqueConstraint("answer_id", name=op.f("uq_qa_answer_evaluations_answer_id")),
    )
    op.create_index(
        op.f("ix_qa_answer_evaluations_answer_id"),
        "qa_answer_evaluations",
        ["answer_id"],
        unique=True,
    )

    op.create_table(
        "final_reports",
        sa.Column("report_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("top_priorities", jsonb, nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("include_qa", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_comparison", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("pdf_status", sa.String(length=30), nullable=False),
        sa.Column("pdf_object_key", sa.Text(), nullable=True),
        sa.Column("is_latest", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_final_reports_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_id", name=op.f("pk_final_reports")),
        sa.UniqueConstraint("rehearsal_id", "version", name=op.f("uq_final_reports_rehearsal_id_version")),
    )
    op.create_index(op.f("ix_final_reports_pdf_status"), "final_reports", ["pdf_status"], unique=False)
    op.create_index(op.f("ix_final_reports_rehearsal_id"), "final_reports", ["rehearsal_id"], unique=False)

    op.create_table(
        "report_scores",
        sa.Column("report_score_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("report_id", sa.BigInteger(), nullable=False),
        sa.Column("score_type", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["final_reports.report_id"],
            name=op.f("fk_report_scores_report_id_final_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_score_id", name=op.f("pk_report_scores")),
        sa.UniqueConstraint("report_id", "score_type", name=op.f("uq_report_scores_report_id_score_type")),
    )
    op.create_index(op.f("ix_report_scores_report_id"), "report_scores", ["report_id"], unique=False)
    op.create_index(op.f("ix_report_scores_score_type"), "report_scores", ["score_type"], unique=False)

    op.create_table(
        "rehearsal_comparisons",
        sa.Column("comparison_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=False),
        sa.Column("base_rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("target_rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("overall_improvement_rate", sa.Numeric(7, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_rehearsal_comparisons_base_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_rehearsal_comparisons_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_rehearsal_comparisons_target_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("comparison_id", name=op.f("pk_rehearsal_comparisons")),
        sa.UniqueConstraint(
            "presentation_id",
            "base_rehearsal_id",
            "target_rehearsal_id",
            name=op.f("uq_rehearsal_comparisons_pair"),
        ),
    )
    op.create_index(
        op.f("ix_rehearsal_comparisons_base_rehearsal_id"),
        "rehearsal_comparisons",
        ["base_rehearsal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rehearsal_comparisons_presentation_id"),
        "rehearsal_comparisons",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rehearsal_comparisons_target_rehearsal_id"),
        "rehearsal_comparisons",
        ["target_rehearsal_id"],
        unique=False,
    )

    op.create_table(
        "comparison_metrics",
        sa.Column("comparison_metric_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("comparison_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("before_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("after_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("change_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("improvement_rate", sa.Numeric(8, 2), nullable=True),
        sa.Column("improved", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["rehearsal_comparisons.comparison_id"],
            name=op.f("fk_comparison_metrics_comparison_id_rehearsal_comparisons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("comparison_metric_id", name=op.f("pk_comparison_metrics")),
        sa.UniqueConstraint("comparison_id", "metric_code", name=op.f("uq_comparison_metrics_comparison_id_metric_code")),
    )
    op.create_index(
        op.f("ix_comparison_metrics_comparison_id"),
        "comparison_metrics",
        ["comparison_id"],
        unique=False,
    )
    op.create_index(op.f("ix_comparison_metrics_metric_code"), "comparison_metrics", ["metric_code"], unique=False)


def downgrade() -> None:
    """Drop agent evaluation, Q&A, report, and comparison tables."""

    op.drop_index(op.f("ix_comparison_metrics_metric_code"), table_name="comparison_metrics")
    op.drop_index(op.f("ix_comparison_metrics_comparison_id"), table_name="comparison_metrics")
    op.drop_table("comparison_metrics")
    op.drop_index(op.f("ix_rehearsal_comparisons_target_rehearsal_id"), table_name="rehearsal_comparisons")
    op.drop_index(op.f("ix_rehearsal_comparisons_presentation_id"), table_name="rehearsal_comparisons")
    op.drop_index(op.f("ix_rehearsal_comparisons_base_rehearsal_id"), table_name="rehearsal_comparisons")
    op.drop_table("rehearsal_comparisons")
    op.drop_index(op.f("ix_report_scores_score_type"), table_name="report_scores")
    op.drop_index(op.f("ix_report_scores_report_id"), table_name="report_scores")
    op.drop_table("report_scores")
    op.drop_index(op.f("ix_final_reports_rehearsal_id"), table_name="final_reports")
    op.drop_index(op.f("ix_final_reports_pdf_status"), table_name="final_reports")
    op.drop_table("final_reports")
    op.drop_index(op.f("ix_qa_answer_evaluations_answer_id"), table_name="qa_answer_evaluations")
    op.drop_table("qa_answer_evaluations")
    op.drop_index(op.f("ix_qa_answers_status"), table_name="qa_answers")
    op.drop_index(op.f("ix_qa_answers_question_id"), table_name="qa_answers")
    op.drop_index(op.f("ix_qa_answers_media_id"), table_name="qa_answers")
    op.drop_table("qa_answers")
    op.drop_index(op.f("ix_qa_question_slides_slide_id"), table_name="qa_question_slides")
    op.drop_table("qa_question_slides")
    op.drop_index(op.f("ix_qa_questions_qa_session_id"), table_name="qa_questions")
    op.drop_index(op.f("ix_qa_questions_category"), table_name="qa_questions")
    op.drop_table("qa_questions")
    op.drop_index(op.f("ix_qa_sessions_status"), table_name="qa_sessions")
    op.drop_index(op.f("ix_qa_sessions_rehearsal_id"), table_name="qa_sessions")
    op.drop_table("qa_sessions")
    op.drop_index(op.f("ix_evaluation_priority_slides_slide_id"), table_name="evaluation_priority_slides")
    op.drop_table("evaluation_priority_slides")
    op.drop_index(op.f("ix_evaluation_priorities_evaluation_id"), table_name="evaluation_priorities")
    op.drop_index(op.f("ix_evaluation_priorities_category"), table_name="evaluation_priorities")
    op.drop_table("evaluation_priorities")
    op.drop_index(op.f("ix_evaluation_criteria_evaluation_id"), table_name="evaluation_criteria")
    op.drop_index(op.f("ix_evaluation_criteria_criterion_code"), table_name="evaluation_criteria")
    op.drop_table("evaluation_criteria")
    op.drop_index(op.f("ix_agent_evaluations_status"), table_name="agent_evaluations")
    op.drop_index(op.f("ix_agent_evaluations_rehearsal_id"), table_name="agent_evaluations")
    op.drop_index(op.f("ix_agent_evaluations_agent_type"), table_name="agent_evaluations")
    op.drop_table("agent_evaluations")
