"""store full entry frames and tracker identifiers

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-13 03:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    with op.batch_alter_table("detections") as batch_op:
        batch_op.add_column(sa.Column("track_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("frame_path", sa.String(), nullable=True))
        batch_op.create_index("ix_detections_track_id", ["track_id"])


def downgrade() -> None:
    with op.batch_alter_table("detections") as batch_op:
        batch_op.drop_index("ix_detections_track_id")
        batch_op.drop_column("frame_path")
        batch_op.drop_column("track_id")
