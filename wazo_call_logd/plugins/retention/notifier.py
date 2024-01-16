# Copyright 2021-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_bus.resources.call_logd.events import CallLogRetentionUpdatedEvent

from .schemas import RetentionSchema


class RetentionNotifier:
    def __init__(self, bus):
        self._bus = bus

    def updated(self, retention):
        payload = RetentionSchema().dump(retention)
        event = CallLogRetentionUpdatedEvent(payload, retention.tenant_uuid)
        self._bus.publish(event)
