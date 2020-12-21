# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytz

from copy import copy
from datetime import datetime
from dateutil.relativedelta import relativedelta

from .exceptions import (
    AgentNotFoundException,
    QueueNotFoundException,
    RangeTooLargeException,
)


class _StatisticsService:
    def _generate_subinterval(self, from_, until, time_delta, timezone):
        from_ = from_.replace(tzinfo=None)
        until = until.replace(tzinfo=None)
        current = from_
        next_datetime = current + time_delta
        while current < until:
            current_in_tz = timezone.normalize(timezone.localize(current))
            next_in_tz = timezone.normalize(timezone.localize(next_datetime))
            yield current_in_tz, next_in_tz
            current = next_in_tz.replace(
                tzinfo=None
            )  # This is essential for DST change
            next_datetime = current + time_delta
            if next_datetime > until:
                next_datetime = until

    def _generate_interval(self, interval, from_, until, timezone):
        time_deltas = {
            'hour': relativedelta(hours=1),
            'day': relativedelta(days=1),
            'month': relativedelta(months=1),
        }

        time_delta = time_deltas.get(interval, 'hour')

        if time_delta == time_deltas['hour']:
            if timezone.normalize(from_ + relativedelta(months=1)) < until:
                raise RangeTooLargeException(
                    details='Maximum of 1 month for interval by hour'
                )
        if interval:
            yield from self._generate_subinterval(from_, until, time_delta, timezone)
        else:
            yield from_, until

    def _get_tomorrow(self, timezone):
        today = timezone.normalize(timezone.localize(datetime.now()))
        return timezone.normalize(
            timezone.localize(
                datetime(today.year, today.month, today.day) + relativedelta(days=1)
            )
        )

    def _datetime_in_week_days(self, date_time, week_days):
        return date_time.isoweekday() in week_days

    def _datetime_in_time_interval(self, date_time, start_time, end_time):
        return start_time <= date_time.hour <= end_time

    def _generate_qos_interval(self, qos_thresholds):
        qos_iter = iter(qos_thresholds)
        prev = next(qos_iter, None)
        yield 0, prev
        if prev is None:
            return
        for current in qos_iter:
            yield prev, current
            prev = current
        yield prev, None


class AgentStatisticsService(_StatisticsService):
    def __init__(self, dao):
        self._dao = dao

    def get(
        self,
        tenant_uuids,
        agent_id,
        timezone,
        from_=None,
        until=None,
        interval=None,
        start_time=None,
        end_time=None,
        week_days=None,
        **kwargs
    ):
        agent_stats = list()
        stat_agent = self._dao.get_stat_agent(agent_id, tenant_uuids)
        if not stat_agent:
            raise AgentNotFoundException(details={'agent_id': agent_id})

        timezone = pytz.timezone(timezone)
        from_ = from_ or timezone.normalize(self._dao.find_oldest_time(agent_id))
        until = until or self._get_tomorrow(timezone)

        if interval:
            for start, end in self._generate_interval(interval, from_, until, timezone):
                if interval == 'hour':
                    if start_time is not None and end_time is not None:
                        if not self._datetime_in_time_interval(
                            start, start_time, end_time
                        ):
                            continue
                        if not self._datetime_in_time_interval(
                            end, start_time, end_time
                        ):
                            continue
                if interval in ('hour', 'day'):
                    if week_days and not self._datetime_in_week_days(start, week_days):
                        continue

                interval_timeframe = {
                    'from': start,
                    'until': end,
                    'agent_id': agent_id,
                    'agent_number': stat_agent['number'],
                    'tenant_uuid': stat_agent['tenant_uuid'],
                }
                interval_stats = (
                    self._dao.get_interval_by_agent(
                        tenant_uuids,
                        agent_id=agent_id,
                        from_=start,
                        until=end,
                        start_time=start_time,
                        end_time=end_time,
                        week_days=week_days,
                        timezone=timezone,
                        **kwargs
                    )
                    or {}
                )
                interval_stats.update(interval_timeframe)
                agent_stats.append(interval_stats)

        period_timeframe = {
            'from': from_,
            'until': until,
            'agent_id': agent_id,
            'agent_number': stat_agent['number'],
            'tenant_uuid': stat_agent['tenant_uuid'],
        }
        period_stats = (
            self._dao.get_interval_by_agent(
                tenant_uuids,
                agent_id=agent_id,
                from_=from_,
                until=until,
                start_time=start_time,
                end_time=end_time,
                week_days=week_days,
                timezone=timezone,
                **kwargs
            )
            or {}
        )
        period_stats.update(period_timeframe)

        agent_stats.append(period_stats)

        return {'total': len(agent_stats), 'items': agent_stats}

    def list(self, tenant_uuids, timezone, from_=None, until=None, **kwargs):
        timezone = pytz.timezone(timezone)
        stat_agents = {
            stat_agent['agent_id']: stat_agent
            for stat_agent in self._dao.get_stat_agents(tenant_uuids)
        }
        agent_stats = {
            agent_stat['agent_id']: agent_stat
            for agent_stat in self._dao.get_interval(
                tenant_uuids, timezone=timezone, from_=from_, until=until, **kwargs
            )
        }
        until = until or self._get_tomorrow(timezone)

        agent_stats_items = []
        for agent_id, stat_agent in stat_agents.items():
            agent_stat = agent_stats.get(agent_id)
            if agent_stat:
                agent_stats_item = copy(agent_stat)
            else:
                agent_stats_item = {}

            from_date = from_
            if not from_date:
                from_date = self._dao.find_oldest_time(agent_id)
                if from_date is not None:
                    from_date = from_date.astimezone(pytz.utc)
                    from_date = timezone.normalize(from_date)

            agent_stats_item.update(
                {
                    'from': from_date,
                    'until': until,
                    'agent_id': stat_agent['agent_id'],
                    'agent_number': stat_agent['number'],
                    'tenant_uuid': stat_agent['tenant_uuid'],
                }
            )
            agent_stats_items.append(agent_stats_item)

        return {
            'items': agent_stats_items,
            'total': len(agent_stats_items),
        }


class QueueStatisticsService(_StatisticsService):
    def __init__(self, dao):
        self._dao = dao

    def get(
        self,
        tenant_uuids,
        queue_id,
        timezone,
        from_=None,
        until=None,
        interval=None,
        start_time=None,
        end_time=None,
        week_days=None,
        **kwargs
    ):
        queue_stats = list()
        stat_queue = self._dao.get_stat_queue(queue_id, tenant_uuids)
        if not stat_queue:
            raise QueueNotFoundException(details={'queue_id': queue_id})

        timezone = pytz.timezone(timezone)
        from_ = from_ or timezone.normalize(self._dao.find_oldest_time(queue_id))
        until = until or self._get_tomorrow(timezone)

        if interval:
            for start, end in self._generate_interval(interval, from_, until, timezone):
                if interval == 'hour':
                    if start_time is not None and end_time is not None:
                        if not self._datetime_in_time_interval(
                            start, start_time, end_time
                        ):
                            continue
                        if not self._datetime_in_time_interval(
                            end, start_time, end_time
                        ):
                            continue
                if interval in ('hour', 'day'):
                    if week_days and not self._datetime_in_week_days(start, week_days):
                        continue

                interval_timeframe = {
                    'from': start,
                    'until': end,
                    'queue_id': queue_id,
                    'queue_name': stat_queue['name'],
                    'tenant_uuid': stat_queue['tenant_uuid'],
                }
                interval_stats = (
                    self._dao.get_interval_by_queue(
                        tenant_uuids,
                        queue_id=queue_id,
                        from_=start,
                        until=end,
                        start_time=start_time,
                        end_time=end_time,
                        week_days=week_days,
                        timezone=timezone,
                        **kwargs
                    )
                    or {}
                )
                interval_stats.update(interval_timeframe)
                queue_stats.append(interval_stats)

        period_timeframe = {
            'from': from_,
            'until': until,
            'queue_id': queue_id,
            'queue_name': stat_queue['name'],
            'tenant_uuid': stat_queue['tenant_uuid'],
        }
        period_stats = (
            self._dao.get_interval_by_queue(
                tenant_uuids,
                queue_id=queue_id,
                from_=from_,
                until=until,
                start_time=start_time,
                end_time=end_time,
                week_days=week_days,
                timezone=timezone,
                **kwargs
            )
            or {}
        )
        period_stats.update(period_timeframe)

        queue_stats.append(period_stats)

        return {
            'items': queue_stats,
            'total': len(queue_stats),
        }

    def get_qos(
        self,
        tenant_uuids,
        queue_id,
        timezone,
        from_=None,
        until=None,
        interval=None,
        start_time=None,
        end_time=None,
        week_days=None,
        qos_thresholds=None,
        **kwargs
    ):
        qos_stats = list()
        stat_queue = self._dao.get_stat_queue(queue_id, tenant_uuids)
        if not stat_queue:
            raise QueueNotFoundException(details={'queue_id': queue_id})

        timezone = pytz.timezone(timezone)
        from_ = from_ or timezone.normalize(self._dao.find_oldest_time(queue_id))
        until = until or self._get_tomorrow(timezone)

        if interval:
            for start, end in self._generate_interval(interval, from_, until, timezone):
                if interval == 'hour':
                    if start_time is not None and end_time is not None:
                        if not self._datetime_in_time_interval(
                            start, start_time, end_time
                        ):
                            continue
                        if not self._datetime_in_time_interval(
                            end, start_time, end_time
                        ):
                            continue
                if interval in ('hour', 'day'):
                    if week_days and not self._datetime_in_week_days(start, week_days):
                        continue

                interval_timeframe = {
                    'from': start,
                    'until': end,
                    'queue_id': queue_id,
                    'queue_name': stat_queue['name'],
                    'tenant_uuid': stat_queue['tenant_uuid'],
                    'quality_of_service': [],
                }
                for qos_min, qos_max in self._generate_qos_interval(qos_thresholds):
                    interval_stats = {
                        'min': qos_min,
                        'max': qos_max,
                        **self._dao.get_qos_interval_by_queue(
                            tenant_uuids,
                            queue_id=queue_id,
                            from_=start,
                            until=end,
                            start_time=start_time,
                            end_time=end_time,
                            week_days=week_days,
                            timezone=timezone,
                            qos_min=qos_min,
                            qos_max=qos_max,
                            **kwargs
                        ),
                    }
                    interval_timeframe['quality_of_service'].append(interval_stats)
                qos_stats.append(interval_timeframe)

        period_timeframe = {
            'from': from_,
            'until': until,
            'queue_id': queue_id,
            'queue_name': stat_queue['name'],
            'tenant_uuid': stat_queue['tenant_uuid'],
            'quality_of_service': [],
        }

        for qos_min, qos_max in self._generate_qos_interval(qos_thresholds):
            period_stats = {
                'min': qos_min,
                'max': qos_max,
                **self._dao.get_qos_interval_by_queue(
                    tenant_uuids,
                    queue_id=queue_id,
                    from_=from_,
                    until=until,
                    start_time=start_time,
                    end_time=end_time,
                    week_days=week_days,
                    timezone=timezone,
                    qos_min=qos_min,
                    qos_max=qos_max,
                    **kwargs
                ),
            }
            period_timeframe['quality_of_service'].append(period_stats)

        qos_stats.append(period_timeframe)

        return {
            'items': qos_stats,
            'total': len(qos_stats),
        }

    def list(self, tenant_uuids, timezone, from_=None, until=None, **kwargs):
        timezone = pytz.timezone(timezone)
        stat_queues = {
            stat_queue['queue_id']: stat_queue
            for stat_queue in self._dao.get_stat_queues(tenant_uuids)
        }
        queue_stats = {
            queue_stat['queue_id']: queue_stat
            for queue_stat in self._dao.get_interval(
                tenant_uuids, timezone=timezone, from_=from_, until=until, **kwargs
            )
        }
        until = until or self._get_tomorrow(timezone)

        queue_stats_items = []
        for queue_id, stat_queue in stat_queues.items():
            queue_stat = queue_stats.get(queue_id)
            if queue_stat:
                queue_stats_item = queue_stat.copy()
            else:
                queue_stats_item = {}

            from_date = from_
            if not from_date:
                from_date = self._dao.find_oldest_time(queue_id)
                if from_date is not None:
                    from_date = from_date.astimezone(pytz.utc)
                    from_date = timezone.normalize(from_date)

            queue_stats_item.update(
                {
                    'from': from_date,
                    'until': until,
                    'queue_id': queue_id,
                    'queue_name': stat_queue['name'],
                    'tenant_uuid': stat_queue['tenant_uuid'],
                }
            )
            queue_stats_items.append(queue_stats_item)

        return {
            'items': queue_stats_items,
            'total': len(queue_stats_items),
        }
