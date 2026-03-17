# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from ..models import VoicemailTranscription
from .base import BaseDAO


class VoicemailTranscriptionDAO(BaseDAO):
    def create(self, transcription_attributes: dict):
        with self.new_session() as session:
            transcription = VoicemailTranscription(**transcription_attributes)
            session.add(transcription)
            session.flush()
            # NOTE: refresh necessary because of create_at server_default
            session.refresh(transcription)
            session.expunge(transcription)
        return transcription

    def update(self, uuid, transcription_attributes: dict):
        with self.new_session() as session:
            transcription = (
                session.query(VoicemailTranscription)
                .filter(VoicemailTranscription.uuid == uuid)
                .one()
            )
            for key, value in transcription_attributes.items():
                setattr(transcription, key, value)
            session.add(transcription)
            session.flush()
            session.expunge(transcription)
            return transcription

    def get_by_message_id(self, message_id, tenant_uuids=None):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription).filter(
                VoicemailTranscription.message_id == message_id,
            )
            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )
            transcription = query.first()
            if transcription:
                session.expunge(transcription)
            return transcription

    def find_all(self, tenant_uuids=None, **params):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription)

            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )

            total = query.count()

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
                escaped = (
                    params['search_text']
                    .replace('\\', r'\\')
                    .replace('%', r'\%')
                    .replace('_', r'\_')
                )
                query = query.filter(
                    VoicemailTranscription.transcription_text.ilike(
                        f'%{escaped}%', escape='\\'
                    )
                )

            filtered = query.count()

            order_field = getattr(
                VoicemailTranscription, params.get('order', 'created_at')
            )
            direction = params.get('direction', 'desc')
            if direction == 'desc':
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field.asc())

            if params.get('offset') is not None:
                query = query.offset(params['offset'])
            if params.get('limit') is not None:
                query = query.limit(params['limit'])

            items = query.all()
            for item in items:
                session.expunge(item)

            return {
                'items': items,
                'total': total,
                'filtered': filtered,
            }

    def delete_by_message_id(self, message_id, tenant_uuids=None):
        with self.new_session() as session:
            query = session.query(VoicemailTranscription).filter(
                VoicemailTranscription.message_id == message_id,
            )
            if tenant_uuids is not None:
                query = query.filter(
                    VoicemailTranscription.tenant_uuid.in_(tenant_uuids)
                )
            deleted = query.delete()
            return deleted > 0
