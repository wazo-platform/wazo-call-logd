"""change_destination_details_key_constraint

Revision ID: 6312d1fb0a91
Revises: 4dfbea039971

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6312d1fb0a91'
down_revision = '4dfbea039971'


def upgrade():
    op.drop_constraint(
        "call_logd_call_log_destination_details_key_check",
        "call_logd_call_log_destination",
        type_="check",
    )
    op.create_check_constraint(
        'call_logd_call_log_destination_details_key_check',
        'call_logd_call_log_destination',
        "destination_details_key IN ('type','user_uuid','user_name', 'meeting_uuid', 'meeting_name', 'conference_id')",
    )


def downgrade():
    op.drop_constraint(
        "call_logd_call_log_destination_details_key_check",
        "call_logd_call_log_destination",
        type_="check",
    )
