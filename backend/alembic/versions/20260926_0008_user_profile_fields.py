"""Add editable account profile fields.

Revision ID: 20260926_0008
Revises: 20260918_0007
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260926_0008"
down_revision: Union[str, None] = "20260918_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("display_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("avatar_data_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("bio", sa.String(length=240), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("bio")
        batch_op.drop_column("avatar_data_url")
        batch_op.drop_column("display_name")
        batch_op.drop_column("full_name")
