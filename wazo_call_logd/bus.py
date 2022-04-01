# Copyright 2022-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.status import Status
from xivo_bus.resources.call_logs.events import (
    CallLogCreatedEvent,
    CallLogUserCreatedEvent,
)
from xivo_bus.consumer import BusConsumer as BaseConsumer
from xivo_bus.publisher import BusPublisher as BasePublisher
from wazo_call_logd.plugins.cdr.schemas import CDRSchema


class BusConsumer(BaseConsumer):
    def provide_status(self, status):
        status['bus_consumer']['status'] = Status.ok if self.is_running else Status.fail


class BusPublisher(BasePublisher):
    def publish_call_log(self, *call_logs):
        for call_log in call_logs:
            event = CallLogCreatedEvent(CDRSchema().dump(call_log))
            headers = {'tenant_uuid': str(call_log.tenant_uuid)}
            super().publish(event, headers)

            serialized = CDRSchema(exclude=['tags']).dump(call_log)
            for participant in call_log.participants:
                user_uuid = participant.user_uuid
                event = CallLogUserCreatedEvent(user_uuid, serialized)
                headers = {
                    'tenant_uuid': str(call_log.tenant_uuid),
                    f'user_uuid:{user_uuid}': True,
                }
                super().publish(event, headers)
