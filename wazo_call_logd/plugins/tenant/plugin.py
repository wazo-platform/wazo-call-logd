# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.bus import BusConsumer
from wazo_call_logd.database.queries import DAO

from .listener import TenantEventHandler


class Plugin:
    def load(self, dependencies):
        dao: DAO = dependencies['dao']
        bus_consumer: BusConsumer = dependencies['bus_consumer']

        tenant_event_handler = TenantEventHandler(dao.tenant)

        tenant_event_handler.subscribe(bus_consumer)
