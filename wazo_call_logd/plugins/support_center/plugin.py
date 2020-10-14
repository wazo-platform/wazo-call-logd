# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO

from .resource import QueuesStatisticsResource, QueueStatisticsResource

from .service import QueueStatisticsService


class Plugin(object):
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']

        dao = DAO(new_db_session(config['db_uri'])).queue_stat
        service = QueueStatisticsService(dao)

        api.add_resource(
            QueuesStatisticsResource,
            '/queues/statistics',
            resource_class_args=[service],
        )
        api.add_resource(
            QueueStatisticsResource,
            '/queues/<int:queue_id>/statistics',
            resource_class_args=[service],
        )
