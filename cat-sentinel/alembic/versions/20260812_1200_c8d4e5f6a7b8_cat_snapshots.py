"""store cat snapshot references and support activity kinds

Revision ID: c8d4e5f6a7b8
Revises: b7c3d9e1f2a4
Create Date: 2026-08-12 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4e5f6a7b8"
down_revision: str | None = "b7c3d9e1f2a4"
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    with op.batch_alter_table("detections") as batch_op:
        batch_op.add_column(sa.Column("snapshot_path", sa.String(), nullable=True))

    with op.batch_alter_table("activities") as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.String(length=9),
            type_=sa.String(length=32),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.String(length=32),
            type_=sa.String(length=9),
            existing_nullable=False,
        )

    with op.batch_alter_table("detections") as batch_op:
        batch_op.drop_column("snapshot_path")
