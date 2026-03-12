# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""add voicemail transcription table

Revision ID: a1b2c3d4e5f6
Revises: 332b72b38735
Create Date: 2026-03-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '332b72b38735'


def upgrade():
    op.create_table(
        'call_logd_voicemail_transcription',
        sa.Column(
            'uuid',
            UUIDType,
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column('message_id', sa.String(255), nullable=False, unique=True),
        sa.Column(
            'tenant_uuid',
            UUIDType,
            sa.ForeignKey(
                'call_logd_tenant.uuid',
                name='call_logd_voicemail_transcription_tenant_uuid_fkey',
                ondelete='CASCADE',
            ),
            nullable=False,
        ),
        sa.Column('voicemail_id', sa.Integer),
        sa.Column('transcription_text', sa.Text, nullable=False),
        sa.Column('provider_id', sa.Text),
        sa.Column('language', sa.String(8)),
        sa.Column('duration', sa.Float),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
    )
    op.create_index(
        'call_logd_voicemail_transcription__idx__message_id',
        'call_logd_voicemail_transcription',
        ['message_id'],
    )
    op.create_index(
        'call_logd_voicemail_transcription__idx__tenant_uuid',
        'call_logd_voicemail_transcription',
        ['tenant_uuid'],
    )
    op.create_index(
        'call_logd_voicemail_transcription__idx__voicemail_id',
        'call_logd_voicemail_transcription',
        ['voicemail_id'],
    )


def downgrade():
    op.drop_table('call_logd_voicemail_transcription')
