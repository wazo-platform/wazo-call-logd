# Copyright 2021-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_bus.resources.call_logd.events import (
    ExportCreatedEvent,
    ExportUpdatedEvent,
)
from .schemas import ExportSchema


class ExportNotifier:
    def __init__(self, bus):
        self._bus = bus

    def created(self, export):
        export_json = ExportSchema().dump(export)
        event = ExportCreatedEvent(export_json)
        headers = {'tenant_uuid': str(export.tenant_uuid)}
        self._bus.publish(event, headers)

    def updated(self, export):
        export_json = ExportSchema().dump(export)
        event = ExportUpdatedEvent(export_json)
        headers = {'tenant_uuid': str(export.tenant_uuid)}
        self._bus.publish(event, headers)
