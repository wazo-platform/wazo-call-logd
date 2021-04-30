"""add exports table

Revision ID: 2b0c06cca84d
Revises: 994326e472b3

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '2b0c06cca84d'
down_revision = '994326e472b3'


def upgrade():
    op.create_table(
        'call_logd_export',
        sa.Column(
            'uuid',
            UUID(as_uuid=True),
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column('tenant_uuid', UUID, nullable=False),
        sa.Column('user_uuid', UUID, nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('done', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('path', sa.Text),
    )
    op.create_foreign_key(
        constraint_name='call_logd_export_tenant_uuid_fkey',
        source_table='call_logd_export',
        referent_table='call_logd_tenant',
        local_cols=['tenant_uuid'],
        remote_cols=['uuid'],
        ondelete='CASCADE',
    )
    op.create_index(
        index_name='call_logd_export__idx__user_uuid',
        table_name='call_logd_export',
        columns=['user_uuid'],
    )


def downgrade():
    op.drop_table('call_logd_export')
