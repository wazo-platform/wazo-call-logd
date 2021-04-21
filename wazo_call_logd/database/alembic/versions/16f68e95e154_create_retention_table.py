"""create-retention-table

Revision ID: 16f68e95e154
Revises: cbd0bbfb6dd8

"""

from alembic import op
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '16f68e95e154'
down_revision = 'cbd0bbfb6dd8'


def upgrade():
    op.create_table(
        'call_logd_retention',
        sa.Column('tenant_uuid', UUID, nullable=False),
        sa.Column('cdr_days', sa.Integer),
        sa.Column('recording_days', sa.Integer),
    )
    op.create_foreign_key(
        constraint_name='call_logd_retention_tenant_uuid_fkey',
        source_table='call_logd_retention',
        referent_table='call_logd_tenant',
        local_cols=['tenant_uuid'],
        remote_cols=['uuid'],
        ondelete='CASCADE',
    )


def downgrade():
    op.drop_table('call_logd_retention')
