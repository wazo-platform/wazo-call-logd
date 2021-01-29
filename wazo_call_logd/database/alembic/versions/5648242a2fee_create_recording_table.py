"""create-recording-table

Revision ID: 5648242a2fee
Revises: None

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '5648242a2fee'
down_revision = None


def upgrade():
    op.create_table(
        'call_logd_recording',
        sa.Column(
            'uuid',
            UUID(as_uuid=True),
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('path', sa.Text),
        sa.Column('call_log_id', sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table('call_logd_recording')
