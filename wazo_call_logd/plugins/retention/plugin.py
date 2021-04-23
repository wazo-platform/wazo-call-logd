# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .http import RetentionResource
from .services import RetentionService
from .notifier import RetentionNotifier


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        dao = dependencies['dao']
        bus_publisher = dependencies['bus_publisher']

        notifier = RetentionNotifier(bus_publisher)
        service = RetentionService(dao, notifier)
        api.add_resource(
            RetentionResource,
            '/retention',
            resource_class_args=[service],
        )
