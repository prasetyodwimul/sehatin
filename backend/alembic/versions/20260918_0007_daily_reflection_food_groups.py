"""Daily reflection and food-group learning state.

Revision ID: 20260918_0007
Revises: 20260918_0006
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_0007"
down_revision: Union[str, None] = "20260918_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("nutrition_program_days") as batch_op:
        batch_op.add_column(sa.Column("food_group_state", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("has_complaint", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("complaint_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nutrition_program_days") as batch_op:
        batch_op.drop_column("complaint_note")
        batch_op.drop_column("has_complaint")
        batch_op.drop_column("food_group_state")
