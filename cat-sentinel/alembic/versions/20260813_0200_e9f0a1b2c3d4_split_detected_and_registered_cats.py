"""split detected identities from registered cat profiles

Revision ID: e9f0a1b2c3d4
Revises: c8d4e5f6a7b8
Create Date: 2026-08-13 02:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "c8d4e5f6a7b8"
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    op.rename_table("cats", "detected_cats")
    op.create_table(
        "registered_cats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("detected_cat_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column(
            "sex",
            sa.Enum("FEMALE", "MALE", "UNKNOWN", name="catsex", native_enum=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["detected_cat_id"], ["detected_cats.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("detected_cat_id"),
    )
    op.create_index("ix_registered_cats_detected_cat_id", "registered_cats", ["detected_cat_id"])
    op.create_index("ix_registered_cats_name", "registered_cats", ["name"])


def downgrade() -> None:
    op.drop_index("ix_registered_cats_name", table_name="registered_cats")
    op.drop_index("ix_registered_cats_detected_cat_id", table_name="registered_cats")
    op.drop_table("registered_cats")
    op.rename_table("detected_cats", "cats")
