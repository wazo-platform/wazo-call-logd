"""add_index_call_logd_call_log_participant__idx__call_log_id

Revision ID: d6a8d09c2f29
Revises: 4dfbea039971

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'd6a8d09c2f29'
down_revision = '4dfbea039971'
INDEX_NAME = 'call_logd_call_log_participant__idx__call_log_id'
TABLE_NAME = 'call_logd_call_log_participant'
ON_COLUMN = 'call_log_id'


def _check_index_exists(index_name):
    conn = op.get_bind()
    result = conn.execute(
        "SELECT exists(SELECT 1 from pg_indexes where indexname = '{}') as ix_exists;".format(
            index_name
        )
    ).first()
    return result.ix_exists


def upgrade():
    if not _check_index_exists(INDEX_NAME):
        op.create_index(
            index_name=INDEX_NAME,
            table_name=TABLE_NAME,
            columns=[ON_COLUMN],
        )


def downgrade():
    op.drop_index(INDEX_NAME)
