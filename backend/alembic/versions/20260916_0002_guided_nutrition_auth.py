"""Controlled auth + guided nutrition persistence.

Revision ID: 20260916_0002
Revises: 20260915_0001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260916_0002"
down_revision: Union[str, None] = "20260915_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_token_hash"), "auth_sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_sessions_expires_at"), "auth_sessions", ["expires_at"], unique=False)

    op.create_table(
        "nutrition_profiles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(20), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("profile_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_nutrition_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_profiles")),
    )
    op.create_index(op.f("ix_nutrition_profiles_user_id"), "nutrition_profiles", ["user_id"], unique=False)
    op.create_index(op.f("ix_nutrition_profiles_stage"), "nutrition_profiles", ["stage"], unique=False)

    with op.batch_alter_table("nutrition_requests") as batch_op:
        batch_op.add_column(sa.Column("height_cm", sa.Float(), nullable=True))

    with op.batch_alter_table("nutrition_recommendations") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("profile_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key("fk_nutrition_recommendations_user_id_users", "users", ["user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_nutrition_recommendations_profile_id_nutrition_profiles", "nutrition_profiles", ["profile_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_nutrition_recommendations_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_nutrition_recommendations_profile_id", ["profile_id"], unique=False)

    op.create_table(
        "nutrition_programs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("recommendation_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_nutrition_programs_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["nutrition_profiles.id"], name=op.f("fk_nutrition_programs_profile_id_nutrition_profiles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["nutrition_recommendations.id"], name=op.f("fk_nutrition_programs_recommendation_id_nutrition_recommendations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_programs")),
    )
    for col in ("user_id", "profile_id", "recommendation_id", "stage", "status"):
        op.create_index(op.f(f"ix_nutrition_programs_{col}"), "nutrition_programs", [col], unique=False)

    op.create_table(
        "nutrition_program_days",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("focus", sa.String(220), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("meal_guidance", sa.Text(), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("checklist_state", sa.JSON(), nullable=False),
        sa.Column("reference_notes", sa.JSON(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["nutrition_programs.id"], name=op.f("fk_nutrition_program_days_program_id_nutrition_programs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_program_days")),
        sa.UniqueConstraint("program_id", "day_number", name="program_day_unique_number"),
    )
    op.create_index(op.f("ix_nutrition_program_days_program_id"), "nutrition_program_days", ["program_id"], unique=False)

    op.create_table(
        "nutrition_meal_logs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("program_day_id", sa.String(36), nullable=True),
        sa.Column("meal_label", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["nutrition_programs.id"], name=op.f("fk_nutrition_meal_logs_program_id_nutrition_programs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_day_id"], ["nutrition_program_days.id"], name=op.f("fk_nutrition_meal_logs_program_day_id_nutrition_program_days"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_meal_logs")),
    )
    op.create_index(op.f("ix_nutrition_meal_logs_program_id"), "nutrition_meal_logs", ["program_id"], unique=False)
    op.create_index(op.f("ix_nutrition_meal_logs_program_day_id"), "nutrition_meal_logs", ["program_day_id"], unique=False)

    op.create_table(
        "nutrition_evaluations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=False),
        sa.Column("guidance_completion", sa.Float(), nullable=False),
        sa.Column("meal_log_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["nutrition_programs.id"], name=op.f("fk_nutrition_evaluations_program_id_nutrition_programs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_evaluations")),
    )
    op.create_index(op.f("ix_nutrition_evaluations_program_id"), "nutrition_evaluations", ["program_id"], unique=False)


def downgrade() -> None:
    op.drop_table("nutrition_evaluations")
    op.drop_table("nutrition_meal_logs")
    op.drop_table("nutrition_program_days")
    op.drop_table("nutrition_programs")
    with op.batch_alter_table("nutrition_recommendations") as batch_op:
        batch_op.drop_index("ix_nutrition_recommendations_profile_id")
        batch_op.drop_index("ix_nutrition_recommendations_user_id")
        batch_op.drop_constraint("fk_nutrition_recommendations_profile_id_nutrition_profiles", type_="foreignkey")
        batch_op.drop_constraint("fk_nutrition_recommendations_user_id_users", type_="foreignkey")
        batch_op.drop_column("profile_id")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("nutrition_requests") as batch_op:
        batch_op.drop_column("height_cm")
    op.drop_table("nutrition_profiles")
    op.drop_table("auth_sessions")
    op.drop_table("users")
