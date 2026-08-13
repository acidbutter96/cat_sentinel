"""cat re-id embedding + alert kind

Adds the columns needed for appearance-based cat re-identification
(cats.embedding, cats.embedding_samples) and for distinguishing
danger-zone alerts from camera-entry alerts (alerts.kind, alerts.zone_id
made nullable). Also drops the (camera_id, track_id) uniqueness constraint
on cats -- track_id is reused across different physical cats over time by
CentroidTracker, so it can no longer be an identity key. See the Cat model
docstring in app/cats/models.py and app/vision/reid.py for the rationale.

Revision ID: b7c3d9e1f2a4
Revises: 48ae57c8e123
Create Date: 2026-08-12 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c3d9e1f2a4'
down_revision: str | None = '48ae57c8e123'
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    with op.batch_alter_table('cats') as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'embedding_samples', sa.Integer(), nullable=False, server_default='0'
            )
        )
        batch_op.drop_constraint('uq_cats_camera_id_track_id', type_='unique')

    with op.batch_alter_table('alerts') as batch_op:
        batch_op.add_column(
            sa.Column(
                'kind',
                sa.Enum('DANGER_ZONE', 'CAMERA_ENTRY', name='alertkind', native_enum=False),
                nullable=False,
                server_default='DANGER_ZONE',
            )
        )
        batch_op.alter_column('zone_id', existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.alter_column('zone_id', existing_type=sa.Uuid(), nullable=False)
        batch_op.drop_column('kind')

    with op.batch_alter_table('cats') as batch_op:
        batch_op.create_unique_constraint(
            'uq_cats_camera_id_track_id', ['camera_id', 'track_id']
        )
        batch_op.drop_column('embedding_samples')
        batch_op.drop_column('embedding')
