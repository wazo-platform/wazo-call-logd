"""queue-destination-details

Revision ID: 57909180a021
Revises: 6190f9a543ef

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '57909180a021'
down_revision = '6190f9a543ef'


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
                'group_label',
                'group_id',
                'queue_name',
                'queue_id',
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
                'group_label',
                'group_id',
            ]
        ),
    )
