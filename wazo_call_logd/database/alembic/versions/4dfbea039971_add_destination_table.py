"""add_destination_table

Revision ID: 4dfbea039971
Revises: 4e193f4c53d0

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = '4dfbea039971'
down_revision = '4e193f4c53d0'


def upgrade():
    op.create_table(
        'call_logd_call_log_destination',
        sa.Column(
            'uuid',
            UUIDType,
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column(
            'destination_details_key',
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            'destination_details_value',
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            'call_log_id',
            sa.Integer,
        ),
    )
    op.create_check_constraint(
        'call_logd_call_log_destination_details_key_check',
        'call_logd_call_log_destination',
        "destination_details_key IN ('type','user_uuid','user_name', 'meeting_uuid', 'meeting_name', 'conference_id')",
    )
    op.create_foreign_key(
        constraint_name='call_logd_call_log_destination_call_log_id_fkey',
        source_table='call_logd_call_log_destination',
        referent_table='call_logd_call_log',
        local_cols=['call_log_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        index_name='call_logd_call_log_destination__idx__uuid',
        table_name='call_logd_call_log_destination',
        columns=['uuid'],
    )


def downgrade():
    op.drop_table('call_logd_call_log_destination')
