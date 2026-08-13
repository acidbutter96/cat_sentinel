"""add registered cat profile images

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-08-13 02:15:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    with op.batch_alter_table("registered_cats") as batch_op:
        batch_op.add_column(sa.Column("photo_path", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("registered_cats") as batch_op:
        batch_op.drop_column("photo_path")
