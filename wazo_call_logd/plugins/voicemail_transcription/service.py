# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from sqlalchemy.exc import IntegrityError

from wazo_call_logd.database.models import VoicemailTranscription
from wazo_call_logd.database.queries import DAO

from .exceptions import TranscriptionNotFoundException

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, dao, bus_publisher):
        self._dao: DAO = dao
        self._bus_publisher = bus_publisher

    def create_transcription(
        self,
        message_id,
        tenant_uuid,
        user_uuid,
        transcription_text,
        provider_id=None,
        language=None,
        duration=None,
    ):
        transcription = VoicemailTranscription(
            voicemail_message_id=message_id,
            tenant_uuid=tenant_uuid,
            user_uuid=user_uuid,
            transcription_text=transcription_text,
            provider_id=provider_id,
            language=language,
            duration=duration,
        )
        try:
            transcription = self._dao.voicemail_transcription.create(transcription)
        except IntegrityError:
            logger.info(
                'Transcription for message %s already exists, skipping', message_id
            )
            return None
        logger.debug('Transcription created for message %s', message_id)
        return transcription

    def get_transcription(self, message_id, tenant_uuids=None, user_uuid=None):
        transcription = self._dao.voicemail_transcription.get_by_message_id(
            message_id, tenant_uuids=tenant_uuids, user_uuid=user_uuid
        )
        if not transcription:
            raise TranscriptionNotFoundException(message_id)
        return transcription

    def list_transcriptions(self, tenant_uuids=None, user_uuid=None, **params):
        return self._dao.voicemail_transcription.find_all(
            tenant_uuids=tenant_uuids, user_uuid=user_uuid, **params
        )

    def delete_transcription(self, message_id, tenant_uuids=None, user_uuid=None):
        deleted = self._dao.voicemail_transcription.delete_by_message_id(
            message_id, tenant_uuids=tenant_uuids, user_uuid=user_uuid
        )
        if deleted:
            logger.debug('Transcription deleted for message %s', message_id)
        return deleted
