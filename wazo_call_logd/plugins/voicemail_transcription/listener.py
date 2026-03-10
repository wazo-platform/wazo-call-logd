# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import TranscriptionService

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionEventHandler:
    service: TranscriptionService

    def subscribe(self, bus_consumer):
        bus_consumer.subscribe(
            'voicemail_transcription_completed',
            self._on_transcription_completed,
        )
        bus_consumer.subscribe(
            'user_voicemail_message_deleted',
            self._on_voicemail_message_deleted,
        )
        bus_consumer.subscribe(
            'global_voicemail_message_deleted',
            self._on_voicemail_message_deleted,
        )

    def _on_transcription_completed(self, event):
        message_id = event['message_id']
        tenant_uuid = event['tenant_uuid']
        user_uuid = event.get('user_uuid')
        transcription_text = event['transcription']
        provider_id = event.get('provider_id')
        language = event.get('language')
        duration = event.get('duration')

        logger.debug(
            'Received transcription completed event for message %s', message_id
        )
        self.service.create_transcription(
            voicemail_message_id=message_id,
            tenant_uuid=tenant_uuid,
            user_uuid=user_uuid,
            transcription_text=transcription_text,
            provider_id=provider_id,
            language=language,
            duration=duration,
        )

    def _on_voicemail_message_deleted(self, event):
        message_id = event['message_id']
        logger.debug(
            'Received voicemail message deleted event for message %s', message_id
        )
        self.service.delete_transcription(message_id)
