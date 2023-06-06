# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_bus.resources.call_logd.events import (
    CallLogExportCreatedEvent,
    CallLogExportUpdatedEvent,
)

from .schemas import ExportSchema


class ExportNotifier:
    def __init__(self, bus):
        self._bus = bus

    def created(self, export):
        payload = ExportSchema().dump(export)
        event = CallLogExportCreatedEvent(payload, export.tenant_uuid)
        self._bus.publish(event)

    def updated(self, export):
        payload = ExportSchema().dump(export)
        event = CallLogExportUpdatedEvent(payload, export.tenant_uuid)
        self._bus.publish(event)
