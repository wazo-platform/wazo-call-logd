# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from sqlalchemy.exc import IntegrityError

from wazo_call_logd.database.queries import DAO

from .exceptions import TranscriptionNotFoundException

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, dao, notifier):
        self._dao: DAO = dao
        self._notifier = notifier

    def create_transcription(
        self,
        message_id,
        tenant_uuid,
        transcription_text,
        voicemail_id=None,
        provider_id=None,
        language=None,
        duration=None,
        **_ignored,
    ):
        attributes = {
            'message_id': message_id,
            'tenant_uuid': tenant_uuid,
            'transcription_text': transcription_text,
            'voicemail_id': voicemail_id,
            'provider_id': provider_id,
            'language': language,
            'duration': duration,
        }
        try:
            transcription = self._dao.voicemail_transcription.create(attributes)
        except IntegrityError as e:
            if not _is_unique_violation(e):
                raise
            logger.info(
                'Transcription for message %s already exists, updating',
                message_id,
            )
            existing = self._dao.voicemail_transcription.get_by_message_id(message_id)
            transcription = self._dao.voicemail_transcription.update(
                existing.uuid, attributes
            )
        self._notifier.created(transcription)
        return transcription

    def list_transcriptions(self, tenant_uuids=None, **params):
        return self._dao.voicemail_transcription.find_all(
            tenant_uuids=tenant_uuids, **params
        )

    def delete_transcription(self, message_id, tenant_uuids=None):
        transcription = self._dao.voicemail_transcription.get_by_message_id(
            message_id, tenant_uuids=tenant_uuids
        )
        if not transcription:
            raise TranscriptionNotFoundException(message_id)
        deleted = self._dao.voicemail_transcription.delete_by_message_id(
            message_id, tenant_uuids=tenant_uuids
        )
        if deleted:
            logger.debug('Transcription deleted for message %s', message_id)
            self._notifier.deleted(message_id, transcription.tenant_uuid)
        return deleted


def _is_unique_violation(exc):
    return getattr(exc.orig, 'pgcode', None) == '23505'
