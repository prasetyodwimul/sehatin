"""Nutrition goals, concrete guidance snapshots, history, and adaptive extensions.

Revision ID: 20260917_0004
Revises: 20260917_0003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260917_0004"
down_revision: Union[str, None] = "20260917_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.add_column(sa.Column("parent_program_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("assessment_snapshot", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("recommendation_snapshot", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("program_config", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.create_index("ix_nutrition_programs_parent_program_id", ["parent_program_id"], unique=False)
        batch_op.create_foreign_key("fk_nutrition_programs_parent_program_id_nutrition_programs", "nutrition_programs", ["parent_program_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("nutrition_program_days") as batch_op:
        batch_op.add_column(sa.Column("action_details", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("meal_guidance_details", sa.JSON(), nullable=False, server_default="{}"))

    op.create_table(
        "nutrition_program_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("goal_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("baseline", sa.Float(), nullable=False),
        sa.Column("target", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=False),
        sa.Column("measurement_method", sa.String(length=120), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("actual", sa.Float(), nullable=False),
        sa.Column("progress_percentage", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["nutrition_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "goal_key", name="program_goal_unique_key"),
    )
    op.create_index("ix_nutrition_program_goals_program_id", "nutrition_program_goals", ["program_id"], unique=False)

    op.create_table(
        "nutrition_program_extensions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_program_id", sa.String(length=36), nullable=False),
        sa.Column("extension_program_id", sa.String(length=36), nullable=False),
        sa.Column("previous_actual", sa.Float(), nullable=False),
        sa.Column("previous_target", sa.Float(), nullable=False),
        sa.Column("remaining_gap", sa.Float(), nullable=False),
        sa.Column("recommended_days", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("guidance_adjustments", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["original_program_id"], ["nutrition_programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extension_program_id"], ["nutrition_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("extension_program_id"),
    )
    op.create_index("ix_nutrition_program_extensions_original_program_id", "nutrition_program_extensions", ["original_program_id"], unique=False)
    op.create_index("ix_nutrition_program_extensions_extension_program_id", "nutrition_program_extensions", ["extension_program_id"], unique=False)

    # Keep safe server defaults for additive compatibility across SQLite tests and PostgreSQL.



def downgrade() -> None:
    op.drop_index("ix_nutrition_program_extensions_extension_program_id", table_name="nutrition_program_extensions")
    op.drop_index("ix_nutrition_program_extensions_original_program_id", table_name="nutrition_program_extensions")
    op.drop_table("nutrition_program_extensions")
    op.drop_index("ix_nutrition_program_goals_program_id", table_name="nutrition_program_goals")
    op.drop_table("nutrition_program_goals")
    with op.batch_alter_table("nutrition_program_days") as batch_op:
        batch_op.drop_column("meal_guidance_details")
        batch_op.drop_column("action_details")
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.drop_constraint("fk_nutrition_programs_parent_program_id_nutrition_programs", type_="foreignkey")
        batch_op.drop_index("ix_nutrition_programs_parent_program_id")
        batch_op.drop_column("program_config")
        batch_op.drop_column("recommendation_snapshot")
        batch_op.drop_column("assessment_snapshot")
        batch_op.drop_column("cycle_number")
        batch_op.drop_column("parent_program_id")
