# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.bus import BusConsumer
from wazo_call_logd.database.queries import DAO

from .bus_consume import TranscriptionEventHandler
from .http import (
    TranscriptionListResource,
    TranscriptionUserItemResource,
    TranscriptionUserListResource,
    TranscriptionUserMeItemResource,
    TranscriptionUserMeListResource,
)
from .notifier import TranscriptionNotifier
from .service import TranscriptionService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        dao: DAO = dependencies['dao']
        bus_consumer: BusConsumer = dependencies['bus_consumer']
        bus_publisher = dependencies['bus_publisher']

        notifier = TranscriptionNotifier(bus_publisher)
        service = TranscriptionService(dao, notifier)
        event_handler = TranscriptionEventHandler(service)
        event_handler.subscribe(bus_consumer)

        api.add_resource(
            TranscriptionListResource,
            '/voicemails/transcriptions',
            resource_class_args=[service],
        )
        api.add_resource(
            TranscriptionUserMeListResource,
            '/users/me/voicemails/transcriptions',
            resource_class_args=[service],
        )
        api.add_resource(
            TranscriptionUserMeItemResource,
            '/users/me/voicemails/<voicemail_message_id>/transcription',
            resource_class_args=[service],
        )
        api.add_resource(
            TranscriptionUserListResource,
            '/users/<uuid:user_uuid>/voicemails/transcriptions',
            resource_class_args=[service],
        )
        api.add_resource(
            TranscriptionUserItemResource,
            '/users/<uuid:user_uuid>/voicemails/<voicemail_message_id>/transcription',
            resource_class_args=[service],
        )
