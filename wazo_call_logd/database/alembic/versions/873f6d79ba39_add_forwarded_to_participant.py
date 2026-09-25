# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""add forwarded to participant

Revision ID: 873f6d79ba39
Revises: 0776735d0419

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '873f6d79ba39'
down_revision = '0776735d0419'

PARTICIPANT_TABLE = 'call_logd_call_log_participant'


def upgrade():
    op.add_column(
        PARTICIPANT_TABLE,
        sa.Column('forwarded', sa.Boolean, nullable=False, server_default='false'),
    )


def downgrade():
    op.drop_column(PARTICIPANT_TABLE, 'forwarded')
