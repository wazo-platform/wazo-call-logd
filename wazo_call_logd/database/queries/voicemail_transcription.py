# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from ..models import VoicemailTranscription
from .base import BaseDAO


class VoicemailTranscriptionDAO(BaseDAO):
    def create(self, transcription):
        with self.new_session() as session:
            session.add(transcription)
            session.flush()
            session.expunge(transcription)
            return transcription

    def get_by_message_id(self, message_id, tenant_uuids=None, user_uuid=None):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription).filter(
                VoicemailTranscription.voicemail_message_id == message_id,
            )
            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )
            if user_uuid is not None:
                query = query.filter(VoicemailTranscription.user_uuid == user_uuid)
            transcription = query.first()
            if transcription:
                session.expunge(transcription)
            return transcription

    def find_all(self, tenant_uuids=None, user_uuid=None, **params):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription)

            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )
            if user_uuid is not None:
                query = query.filter(VoicemailTranscription.user_uuid == user_uuid)
            if params.get('voicemail_id') is not None:
                query = query.filter(
                    VoicemailTranscription.voicemail_id.in_(params['voicemail_id'])
                )
            if params.get('start'):
                query = query.filter(
                    VoicemailTranscription.created_at >= params['start']
                )
            if params.get('end'):
                query = query.filter(VoicemailTranscription.created_at < params['end'])
            if params.get('search_text'):
                query = query.filter(
                    VoicemailTranscription.transcription_text.ilike(
                        f'%{params["search_text"]}%'
                    )
                )

            total = query.count()

            order_field = getattr(
                VoicemailTranscription,
                params.get('order', 'created_at'),
                VoicemailTranscription.created_at,
            )
            direction = params.get('direction', 'desc')
            if direction == 'desc':
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field.asc())

            filtered = total

            if params.get('offset'):
                query = query.offset(params['offset'])
            if params.get('limit'):
                query = query.limit(params['limit'])

            items = query.all()
            for item in items:
                session.expunge(item)

            return {
                'items': items,
                'total': total,
                'filtered': filtered,
            }

    def delete_by_message_id(self, message_id, tenant_uuids=None, user_uuid=None):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription).filter(
                VoicemailTranscription.voicemail_message_id == message_id,
            )
            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )
            if user_uuid is not None:
                query = query.filter(VoicemailTranscription.user_uuid == user_uuid)
            deleted = query.delete()
            return deleted > 0
