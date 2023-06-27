# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask_restful import Api

from wazo_call_logd.bus import BusConsumer, BusPublisher
from wazo_call_logd.database.queries import DAO

from .http import RetentionResource
from .listener import RetentionListener
from .notifier import RetentionNotifier
from .services import RetentionService


class Plugin:
    def load(self, dependencies):
        api: Api = dependencies['api']
        dao: DAO = dependencies['dao']
        bus_publisher: BusPublisher = dependencies['bus_publisher']
        bus_consumer: BusConsumer = dependencies['bus_consumer']

        notifier = RetentionNotifier(bus_publisher)
        service = RetentionService(dao, notifier)
        listener = RetentionListener(dao.retention)

        bus_consumer.subscribe('auth_tenant_deleted', listener.tenant_deleted)

        api.add_resource(
            RetentionResource,
            '/retention',
            resource_class_args=[service],
        )
