# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .exceptions import QueueNotFoundException


class QueueStatisticsService(object):
    def __init__(self, dao):
        self._dao = dao

    def get(self, tenant_uuids, queue_id, **kwargs):
        queue_stats = self._dao.get_interval_by_queue(tenant_uuids, queue_id=queue_id, **kwargs)
        if not queue_stats:
            raise QueueNotFoundException(details={'queue_id': queue_id})

        return {
            'items': [queue_stats],
            'total': count,
        }

    def list(self, tenant_uuids, **kwargs):
        queue_stats = self._dao.get_interval(tenant_uuids, **kwargs)
        count = len(queue_stats)
        return {
            'items': queue_stats,
            'total': count,
        }
