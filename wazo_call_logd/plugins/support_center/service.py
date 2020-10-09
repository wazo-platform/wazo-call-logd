# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from .exceptions import QueueNotFoundException, RangeTooLargeException


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
            today = datetime.now(tz=timezone.utc)
            until = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + relativedelta(days=1)

        if not from_:
            interval = None

        time_delta = time_deltas.get(interval, 'hour')

        if time_delta == time_deltas['hour']:
            if from_ + relativedelta(months=1) < until:
                raise RangeTooLargeException(
                    details='Maximum of 1 month for interval by hour'
                )
        if interval:
            current = from_
            next_datetime = current + time_delta
            while current < until:
                yield current, next_datetime
                current = next_datetime
                next_datetime = current + time_delta
                if next_datetime > until:
                    next_datetime = until
        else:
            yield from_, until

    def get(self, tenant_uuids, queue_id, **kwargs):
        queue_stats = list()

        interval = kwargs.pop('interval', None)
        from_ = kwargs.pop('from_', None)
        until = kwargs.pop('until', None)

        if interval:
            for start, end in self._generate_interval(interval, from_, until):
                interval_timeframe = {
                    'from': start,
                    'until': end,
                }
                interval_stats = self._dao.get_interval_by_queue(
                    tenant_uuids, queue_id=queue_id, from_=start, until=end, **kwargs
                ) or {}
                interval_stats.update(interval_timeframe)
                queue_stats.append(interval_stats)

        period_timeframe = {
            'from': from_,
            'until': until,
        }
        period_stats = self._dao.get_interval_by_queue(
            tenant_uuids, queue_id=queue_id, from_=from_, until=until, **kwargs
        ) or {}
        period_stats.update(period_timeframe)

        queue_stats.append(period_stats)

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
                **queue_stat
            }
            queue_stats_item.update({
                'from': from_,
                'until': until,
            })
            queue_stats_items.append(queue_stats_item)

        return {
            'items': queue_stats_items,
            'total': len(queue_stats),
        }
