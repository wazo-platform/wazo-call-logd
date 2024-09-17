"""add-requested-participant

Revision ID: 08ba4cd18b85
Revises: 2ff862045893

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '08ba4cd18b85'
down_revision = '2ff862045893'

TABLE_NAME = 'call_logd_call_log_participant'
COLUMN_NAME = 'requested'


def upgrade():
    op.add_column(
        TABLE_NAME,
        sa.Column(COLUMN_NAME, sa.Boolean, server_default=sa.false(), nullable=False),
    )


def downgrade():
    op.drop_column(TABLE_NAME, COLUMN_NAME)
