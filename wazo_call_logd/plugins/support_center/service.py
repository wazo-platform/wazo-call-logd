# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class QueueStatisticsService(object):
    def __init__(self, dao):
        self._dao = dao

    def get(self, tenant_uuids, queue_id, **kwargs):
        queue_stats = self._dao.get_interval_by_queue(tenant_uuids, queue_id=queue_id, **kwargs)
        count = len(queue_stats)
        return {
            'items': call_logs,
            'total': count,
        }

    def list(self, tenant_uuids, **kwargs):
        queue_stats = self._dao.get_interval(tenant_uuids, **kwargs)
        count = len(queue_stats)
        return {
            'items': queue_stats,
            'total': count,
        }
