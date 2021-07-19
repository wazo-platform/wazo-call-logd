"""add the source_internal_name column

Revision ID: 4e193f4c53d0
Revises: 48427e863c39

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4e193f4c53d0'
down_revision = '48427e863c39'

TABLE_NAME = 'call_logd_call_log'
COLUMN_NAME = 'source_internal_name'


def upgrade():
    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Text))


def downgrade():
    op.drop_column(TABLE_NAME, COLUMN_NAME)
