"""add missing call-log index

Revision ID: 6190f9a543ef
Revises: 08ba4cd18b85

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '6190f9a543ef'
down_revision = '08ba4cd18b85'

INDEXES = [
    (
        'call_logd_call_log_destination__idx__call_log_id',
        'call_logd_call_log_destination',
        'call_log_id',
    ),
    (
        'call_logd_recording__idx__call_log_id',
        'call_logd_recording',
        'call_log_id',
    ),
]


def upgrade():
    for idx_name, tbl_name, col_name in INDEXES:
        op.create_index(
            index_name=idx_name,
            table_name=tbl_name,
            columns=[col_name],
        )


def downgrade():
    for idx_name, _, __ in INDEXES:
        op.drop_index(idx_name)
