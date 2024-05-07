"""group-destination-details

Revision ID: 9cafdec9b563
Revises: d6a8d09c2f29

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = '9cafdec9b563'
down_revision = 'd6a8d09c2f29'

destination_table = sa.table(
    'call_logd_call_log_destination',
    sa.column(
        'uuid',
    ),
    sa.column(
        'destination_details_key',
    ),
    sa.column(
        'destination_details_value',
    ),
    sa.column(
        'call_log_id',
    ),
)


def upgrade():
    op.drop_constraint(
        constraint_name='call_logd_call_log_destination_details_key_check',
        table_name='call_logd_call_log_destination',
    )
    op.create_check_constraint(
        constraint_name='call_logd_call_log_destination_details_key_check',
        table_name='call_logd_call_log_destination',
        condition=destination_table.c.destination_details_key.in_(
            [
                'type',
                'user_uuid',
                'user_name',
                'meeting_uuid',
                'meeting_name',
                'conference_id',
                'group_name',
                'group_id',
            ]
        ),
    )


def downgrade():
    op.drop_constraint(
        constraint_name='call_logd_call_log_destination_details_key_check',
        table_name='call_logd_call_log_destination',
    )
    op.create_check_constraint(
        constraint_name='call_logd_call_log_destination_details_key_check',
        table_name='call_logd_call_log_destination',
        condition=destination_table.c.destination_details_key.in_(
            [
                'type',
                'user_uuid',
                'user_name',
                'meeting_uuid',
                'meeting_name',
                'conference_id',
            ]
        ),
    )
