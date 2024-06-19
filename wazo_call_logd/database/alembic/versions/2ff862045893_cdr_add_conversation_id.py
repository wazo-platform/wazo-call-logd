"""cdr_add_conversation_id

Revision ID: 2ff862045893
Revises: 9cafdec9b563

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2ff862045893'
down_revision = '9cafdec9b563'

CALL_LOG_TABLE_NAME = 'call_logd_call_log'
CALL_LOG_INDEX_NAME = f'{CALL_LOG_TABLE_NAME}__idx__conversation_id'


def upgrade():
    op.add_column(CALL_LOG_TABLE_NAME, sa.Column('conversation_id', sa.String(255)))
    op.create_index(
        index_name=CALL_LOG_INDEX_NAME,
        table_name=CALL_LOG_TABLE_NAME,
        columns=['conversation_id'],
    )


def downgrade():
    op.drop_index(CALL_LOG_INDEX_NAME)
    op.drop_column(CALL_LOG_TABLE_NAME, 'conversation_id')
