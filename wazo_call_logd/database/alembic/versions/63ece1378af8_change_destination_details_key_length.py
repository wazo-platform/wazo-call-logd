"""change_destination_details_key_length

Revision ID: 63ece1378af8
Revises: 6312d1fb0a91

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '63ece1378af8'
down_revision = '6312d1fb0a91'


def upgrade():
    op.alter_column(
        'call_logd_call_log_destination',
        'destination_details_key',
        nullable=False,
        type_=sa.String(32),
    )


def downgrade():
    op.alter_column(
        'call_logd_call_log_destination',
        'destination_details_key',
        nullable=False,
        type_=sa.String(10),
    )
