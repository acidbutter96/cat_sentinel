"""create recordings table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-09 17:11:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

recording_status = sa.Enum(
    "recording", "completed", "failed", "missing", name="recording_status"
)


def upgrade() -> None:
    op.create_table(
        "recordings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", recording_status, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recordings_filename"), "recordings", ["filename"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_recordings_filename"), table_name="recordings")
    op.drop_table("recordings")
