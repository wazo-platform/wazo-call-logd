# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_bus.resources.call_logd.events import (
    VoicemailTranscriptionCreatedEvent,
    VoicemailTranscriptionDeletedEvent,
)

from .schemas import TranscriptionSchema


class TranscriptionNotifier:
    def __init__(self, bus):
        self._bus = bus

    def created(self, transcription):
        payload = TranscriptionSchema().dump(transcription)
        event = VoicemailTranscriptionCreatedEvent(
            payload, str(transcription.tenant_uuid)
        )
        self._bus.publish(event)

    def deleted(self, transcription):
        payload = TranscriptionSchema().dump(transcription)
        event = VoicemailTranscriptionDeletedEvent(
            payload, str(transcription.tenant_uuid)
        )
        self._bus.publish(event)
