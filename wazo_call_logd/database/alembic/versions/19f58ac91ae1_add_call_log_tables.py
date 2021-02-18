"""add-call-log-tables

Revision ID: 19f58ac91ae1
Revises: 5648242a2fee

"""

from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '19f58ac91ae1'
down_revision = '5648242a2fee'


def upgrade():
    op.create_table(
        'call_logd_call_log',
        sa.Column('id', sa.Integer, nullable=False, primary_key=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('date_answer', sa.DateTime(timezone=True)),
        sa.Column('date_end', sa.DateTime(timezone=True)),
        sa.Column('tenant_uuid', UUID, nullable=False),
        sa.Column('source_name', sa.String(255)),
        sa.Column('source_exten', sa.String(255)),
        sa.Column('source_internal_exten', sa.Text),
        sa.Column('source_internal_context', sa.Text),
        sa.Column('source_line_identity', sa.String(255)),
        sa.Column('requested_name', sa.Text),
        sa.Column('requested_exten', sa.String(255)),
        sa.Column('requested_context', sa.String(255)),
        sa.Column('requested_internal_exten', sa.Text),
        sa.Column('requested_internal_context', sa.Text),
        sa.Column('destination_name', sa.String(255)),
        sa.Column('destination_exten', sa.String(255)),
        sa.Column('destination_internal_exten', sa.Text),
        sa.Column('destination_internal_context', sa.Text),
        sa.Column('destination_line_identity', sa.String(255)),
        sa.Column('direction', sa.String(255)),
        sa.Column('user_field', sa.String(255)),
    )
    op.create_check_constraint(
        'call_logd_call_log_direction_check',
        'call_logd_call_log',
        "direction IN ('inbound','internal','outbound')",
    )
    op.create_table(
        'call_logd_call_log_participant',
        sa.Column('uuid', UUID, primary_key=True),
        sa.Column('call_log_id', sa.Integer),
        sa.Column('user_uuid', UUID, nullable=False),
        sa.Column('line_id', sa.Integer),
        sa.Column(
            'role',
            sa.Enum('source', 'destination', name='call_logd_call_log_participant_role'),
            nullable=False,
        ),
        sa.Column('tags', ARRAY(sa.String(128)), nullable=False, server_default='{}'),
        sa.Column('answered', sa.Boolean, nullable=False, server_default='false'),
    )
    op.create_foreign_key(
        constraint_name='call_logd_call_log_participant_call_log_id_fkey',
        source_table='call_logd_call_log_participant',
        referent_table='call_logd_call_log',
        local_cols=['call_log_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        index_name='call_logd_call_log_participant__idx__user_uuid',
        table_name='call_logd_call_log_participant',
        columns=['user_uuid'],
    )


def downgrade():
    op.drop_table('call_logd_call_log_participant')
    op.drop_table('call_logd_call_log')
