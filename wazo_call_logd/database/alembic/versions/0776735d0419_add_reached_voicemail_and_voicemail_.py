# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""add reached_voicemail and voicemail destination details

Revision ID: 0776735d0419
Revises: 48f5f29349c2

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0776735d0419'
down_revision = '48f5f29349c2'

DESTINATION_TABLE = 'call_logd_call_log_destination'
DESTINATION_KEY_CHECK = 'call_logd_call_log_destination_details_key_check'

OLD_KEYS = (
    'type',
    'user_uuid',
    'user_name',
    'meeting_uuid',
    'meeting_name',
    'conference_id',
    'group_label',
    'group_id',
)
VOICEMAIL_KEYS = ('voicemail_id', 'voicemail_name')
NEW_KEYS = OLD_KEYS + VOICEMAIL_KEYS


def _key_in(keys):
    return sa.column('destination_details_key').in_(keys)


def upgrade():
    op.add_column(
        'call_logd_call_log',
        sa.Column('reached_voicemail', sa.Boolean),
    )
    op.drop_constraint(DESTINATION_KEY_CHECK, DESTINATION_TABLE, type_='check')
    op.create_check_constraint(
        DESTINATION_KEY_CHECK, DESTINATION_TABLE, _key_in(NEW_KEYS)
    )


def downgrade():
    op.drop_constraint(DESTINATION_KEY_CHECK, DESTINATION_TABLE, type_='check')
    # Drop the whole voicemail destination group: a surviving type='voicemail'
    # row passes OLD_KEYS but makes rolled-back code KeyError on serialization.
    # Must run before recreating OLD_KEYS, which Postgres validates against rows.
    destination = sa.table(
        DESTINATION_TABLE,
        sa.column('call_log_id'),
        sa.column('destination_details_key'),
        sa.column('destination_details_value'),
    )
    voicemail_call_logs = sa.select(destination.c.call_log_id).where(
        sa.and_(
            destination.c.destination_details_key == 'type',
            destination.c.destination_details_value == 'voicemail',
        )
    )
    op.execute(
        destination.delete().where(destination.c.call_log_id.in_(voicemail_call_logs))
    )
    op.create_check_constraint(
        DESTINATION_KEY_CHECK, DESTINATION_TABLE, _key_in(OLD_KEYS)
    )
    op.drop_column('call_logd_call_log', 'reached_voicemail')
