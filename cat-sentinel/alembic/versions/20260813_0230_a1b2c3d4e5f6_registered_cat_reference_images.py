"""store registered cat reference images for recognition

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-08-13 02:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    with op.batch_alter_table("detected_cats") as batch_op:
        batch_op.add_column(sa.Column("registered_cat_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_detected_cats_registered_cat_id",
            "registered_cats",
            ["registered_cat_id"],
            ["id"],
        )
        batch_op.create_index("ix_detected_cats_registered_cat_id", ["registered_cat_id"])

    op.create_table(
        "registered_cat_reference_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("registered_cat_id", sa.Uuid(), nullable=False),
        sa.Column("image_path", sa.String(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["registered_cat_id"], ["registered_cats.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("image_path"),
    )
    op.create_index(
        "ix_registered_cat_reference_images_registered_cat_id",
        "registered_cat_reference_images",
        ["registered_cat_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_registered_cat_reference_images_registered_cat_id",
        table_name="registered_cat_reference_images",
    )
    op.drop_table("registered_cat_reference_images")

    with op.batch_alter_table("detected_cats") as batch_op:
        batch_op.drop_index("ix_detected_cats_registered_cat_id")
        batch_op.drop_constraint("fk_detected_cats_registered_cat_id", type_="foreignkey")
        batch_op.drop_column("registered_cat_id")
