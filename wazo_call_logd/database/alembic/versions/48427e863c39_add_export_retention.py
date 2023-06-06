"""add export retention

Revision ID: 48427e863c39
Revises: 2b0c06cca84d

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '48427e863c39'
down_revision = '2b0c06cca84d'

CONFIG_TABLE_NAME = 'call_logd_config'
RETENTION_TABLE_NAME = 'call_logd_retention'


def upgrade():
    op.add_column(
        RETENTION_TABLE_NAME,
        sa.Column('export_days', sa.Integer),
    )
    op.add_column(
        CONFIG_TABLE_NAME,
        sa.Column('retention_export_days', sa.Integer, server_default='2'),
    )
    op.add_column(
        CONFIG_TABLE_NAME,
        sa.Column(
            'retention_export_days_from_file',
            sa.Boolean,
            server_default='false',
            nullable=False,
        ),
    )
    op.alter_column(
        CONFIG_TABLE_NAME,
        'retention_export_days',
        server_default=None,
    )
    op.alter_column(
        CONFIG_TABLE_NAME,
        'retention_export_days_from_file',
        server_default=None,
    )


def downgrade():
    op.drop_column(CONFIG_TABLE_NAME, 'retention_export_days')
    op.drop_column(CONFIG_TABLE_NAME, 'retention_export_days_from_file')
    op.drop_column(RETENTION_TABLE_NAME, 'export_days')
