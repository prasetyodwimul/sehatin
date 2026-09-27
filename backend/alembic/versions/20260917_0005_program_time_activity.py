"""Program calendar progress and activity tracking.

Revision ID: 20260917_0005
Revises: 20260917_0004
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260917_0005"
down_revision: Union[str, None] = "20260917_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.add_column(sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nutrition_programs") as batch_op:
        batch_op.drop_column("last_activity_at")
