"""add column call_log.blocked

Revision ID: fc88d78f53b8
Revises: 6190f9a543ef

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fc88d78f53b8'
down_revision = '6190f9a543ef'

TABLE_NAME = 'call_logd_call_log'
COLUMN_NAME = 'blocked'


def upgrade():
    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Boolean))


def downgrade():
    op.drop_column(TABLE_NAME, COLUMN_NAME)
