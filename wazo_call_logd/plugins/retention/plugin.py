# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .http import RetentionResource
from .services import RetentionService
from .notifier import RetentionNotifier
from .listener import RententionListener

from wazo_call_logd.bus import BusConsumer, BusPublisher
from wazo_call_logd.database.queries import DAO
from flask_restful import Api


class Plugin:
    def load(self, dependencies):
        api: Api = dependencies['api']
        dao: DAO = dependencies['dao']
        bus_publisher: BusPublisher = dependencies['bus_publisher']
        bus_consumer: BusConsumer = dependencies['bus_consumer']

        notifier = RetentionNotifier(bus_publisher)
        service = RetentionService(dao, notifier)
        listener = RententionListener(dao.retention)

        bus_consumer.subscribe('auth_tenant_deleted', listener.tenant_deleted)

        api.add_resource(
            RetentionResource,
            '/retention',
            resource_class_args=[service],
        )
