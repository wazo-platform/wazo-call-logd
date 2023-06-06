"""add-config-table

Revision ID: 994326e472b3
Revises: 16f68e95e154

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '994326e472b3'
down_revision = '16f68e95e154'


def upgrade():
    op.create_table(
        'call_logd_config',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('retention_cdr_days', sa.Integer),
        sa.Column('retention_cdr_days_from_file', sa.Boolean, nullable=False),
        sa.Column('retention_recording_days', sa.Integer),
        sa.Column('retention_recording_days_from_file', sa.Boolean, nullable=False),
    )


def downgrade():
    op.drop_table('call_logd_config')
