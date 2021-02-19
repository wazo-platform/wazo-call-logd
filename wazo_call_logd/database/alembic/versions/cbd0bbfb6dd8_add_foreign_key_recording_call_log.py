"""add-foreign-key-recording-call-log

Revision ID: cbd0bbfb6dd8
Revises: 19f58ac91ae1

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cbd0bbfb6dd8'
down_revision = '19f58ac91ae1'

recording_tbl = sa.sql.table('call_logd_recording')


def upgrade():
    query = recording_tbl.delete()
    op.execute(query)
    op.create_foreign_key(
        constraint_name='call_logd_recording_call_log_id_fkey',
        source_table='call_logd_recording',
        referent_table='call_logd_call_log',
        local_cols=['call_log_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
    )


def downgrade():
    op.drop_constraint('call_logd_recording_call_log_id_fkey', 'call_logd_recording')
