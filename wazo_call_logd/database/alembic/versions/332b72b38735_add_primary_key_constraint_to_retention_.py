"""add primary key constraint to retention table

Revision ID: 332b72b38735
Revises: fc88d78f53b8

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '332b72b38735'
down_revision = 'fc88d78f53b8'


def upgrade():
    op.create_primary_key(
        'call_logd_retention_pkey', 'call_logd_retention', ['tenant_uuid']
    )


def downgrade():
    op.drop_constraint(
        'call_logd_retention_pkey', 'call_logd_retention', type_='primary'
    )
