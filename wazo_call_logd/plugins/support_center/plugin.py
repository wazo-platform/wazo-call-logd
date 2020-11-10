# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO

from .resource import (
    AgentsStatisticsResource,
    AgentStatisticsResource,
    QueuesStatisticsResource,
    QueueStatisticsResource,
)

from .service import AgentStatisticsService, QueueStatisticsService


class Plugin(object):
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']

        dao = DAO(new_db_session(config['db_uri']))
        queue_service = QueueStatisticsService(dao.queue_stat)
        agent_service = AgentStatisticsService(dao.agent_stat)

        api.add_resource(
            AgentsStatisticsResource,
            '/agents/statistics',
            resource_class_args=[agent_service],
        )
        api.add_resource(
            AgentStatisticsResource,
            '/agents/<int:agent_id>/statistics',
            resource_class_args=[agent_service],
        )
        api.add_resource(
            QueuesStatisticsResource,
            '/queues/statistics',
            resource_class_args=[queue_service],
        )
        api.add_resource(
            QueueStatisticsResource,
            '/queues/<int:queue_id>/statistics',
            resource_class_args=[queue_service],
        )
