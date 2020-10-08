# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from .exceptions import QueueNotFoundException


class QueueStatisticsService(object):
    def __init__(self, dao):
        self._dao = dao

    def _generate_interval(self, interval, from_, until):
        time_deltas = {
            'hour': relativedelta(hours=1),
            'day': relativedelta(days=1),
            'month': relativedelta(months=1),
        }

        if not until:
            until = date.today() + relativedelta(days=1)

        if not from_:
            interval = None

        time_delta = time_deltas.get(interval, 'hour')
        if interval:
            current = from_
            while current < until:
                next_datetime = current + time_delta
                yield current, next_datetime
                current = next_datetime
        else:
            yield None, None

    def get(self, tenant_uuids, queue_id, **kwargs):
        queue_stats = list()

        interval = kwargs.pop('interval', None)
        from_ = kwargs.pop('from_', None)
        until = kwargs.pop('until', None)

        for start, end in self._generate_interval(interval, from_, until):
            queue_stat = {
                'from': start,
                'until': end,
            }
            interval_stat = self._dao.get_interval_by_queue(
                tenant_uuids, queue_id=queue_id, from_=start, until=end, **kwargs
            )
            if interval_stat:
                queue_stat.update(interval_stat)

            queue_stats.append(queue_stat)


        whole_interval_stats = {
            'from': from_,
            'until': until,
        }
        period_stats = self._dao.get_interval_by_queue(
            tenant_uuids, queue_id=queue_id, from_=from_, until=until, **kwargs
        )
        if period_stats:
            whole_interval_stats.update(period_stats)

        queue_stats.append(whole_interval_stats)

        if not queue_stats:
            raise QueueNotFoundException(details={'queue_id': queue_id})

        return {
            'items': queue_stats,
            'total': len(queue_stats),
        }

    def list(self, tenant_uuids, **kwargs):

        queue_stats = self._dao.get_interval(tenant_uuids, **kwargs)
        from_ = kwargs.pop('from_', None)
        until = kwargs.pop('until', None)

        queue_stats_items = []
        for queue_stat in queue_stats:
            queue_stats_item = {
                'from': from_,
                'until': until,
                **queue_stat
            }
            queue_stats_items.append(queue_stats_item)

        return {
            'items': queue_stats_items,
            'total': len(queue_stats),
        }
