# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .exceptions import TranscriptionNotFoundException

if TYPE_CHECKING:
    from wazo_bus.resources.webhookd.types import VoicemailTranscriptionCompletedPayload

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

    def _on_transcription_completed(
        self, event: VoicemailTranscriptionCompletedPayload
    ):
        message_id = event['message_id']
        logger.debug(
            'Received transcription completed event for message %s',
            message_id,
        )
        self.service.create_transcription(**event)

    def _on_voicemail_message_deleted(self, event):
        message_id = event['message_id']
        logger.debug(
            'Received voicemail message deleted event for message %s', message_id
        )
        try:
            self.service.delete_transcription(message_id)
        except TranscriptionNotFoundException:
            logger.debug(
                'No transcription found for deleted voicemail message %s', message_id
            )
