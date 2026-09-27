"""Program completion and sequential progress state.

Revision ID: 20260917_0003
Revises: 20260916_0002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260917_0003"
down_revision: Union[str, None] = "20260916_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # Normalize pre-existing sprint rows without discarding user data.
    op.execute("UPDATE nutrition_programs SET status = UPPER(status) WHERE status IS NOT NULL")


def downgrade() -> None:
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.drop_column("completed_at")
