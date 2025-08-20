"""add queue destination

Revision ID: 3da07fc55d1f
Revises: fc88d78f53b8

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '3da07fc55d1f'
down_revision = 'fc88d78f53b8'

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
                'queue_label',
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
