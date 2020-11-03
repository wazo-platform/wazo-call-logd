# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import func, text

from xivo_dao.alchemy.stat_call_on_queue import StatCallOnQueue
from xivo_dao.alchemy.stat_queue import StatQueue
from xivo_dao.alchemy.stat_queue_periodic import StatQueuePeriodic

from .base import BaseDAO

from marshmallow import Schema, fields


class StatRow(Schema):
    queue_id = fields.Integer()
    queue_name = fields.String()
    from_ = fields.DateTime(attribute='from', data_key='from')
    until = fields.DateTime()
    tenant_uuid = fields.UUID()
    answered = fields.Integer()
    abandoned = fields.Integer()
    total = fields.Integer()
    full = fields.Integer()
    closed = fields.Integer()
    joinempty = fields.Integer()
    leaveempty = fields.Integer()
    divert_ca_ratio = fields.Integer()
    divert_waittime = fields.Integer()
    timeout = fields.Integer()


class QueueStatDAO(BaseDAO):
    def find_oldest_time(self, queue_id):
        with self.new_session() as session:
            query = (
                session.query(StatQueuePeriodic.time)
                .join(StatQueue)
                .filter(StatQueue.queue_id == queue_id)
                .order_by(StatQueuePeriodic.time.asc())
                .limit(1)
            )
            return query.scalar()

    def find_stat_queues(self, tenant_uuids=None):
        with self.new_session() as session:
            query = session.query(
                StatQueue.queue_id, StatQueue.name, StatQueue.tenant_uuid
            )

            if tenant_uuids:
                query = query.filter(StatQueue.tenant_uuid.in_(tenant_uuids))

            return query.all()

    def get_interval_by_queue(self, tenant_uuids, queue_id, **filters):
        with self.new_session() as session:
            query = self._queue_stat_query(
                session, tenant_uuids=tenant_uuids, **filters
            )
            query = query.filter(StatQueue.queue_id == queue_id)
            row = query.first()
            result = None
            if row:
                basic_stats = StatRow().dump(row)
                extra_stats = self._get_extra_stats(session, basic_stats, **filters)
                result = {**basic_stats, **extra_stats}
            session.expunge_all()
        return result

    def get_interval(self, tenant_uuids, **filters):
        with self.new_session() as session:
            query = self._queue_stat_query(
                session, tenant_uuids=tenant_uuids, **filters
            )
            rows = query.all()
            results = []
            for row in rows:
                basic_stats = StatRow().dump(row)
                extra_stats = self._get_extra_stats(session, basic_stats, **filters)
                results.append({**basic_stats, **extra_stats})
            session.expunge_all()
        return results

    def _extract_timezone_to_postgres_format(self, from_):
        tz_offset = from_.strftime('%z') or '+0000'
        return '{}:{}'.format(tz_offset[0:3], tz_offset[3:])

    # NOTE(fblackburn): This only work because tables used have same column name
    def _add_interval_query(
        self,
        table,
        query,
        tenant_uuids=None,
        week_days=None,
        start_time=None,
        end_time=None,
        from_=None,
        until=None,
        **ignored,
    ):
        if tenant_uuids:
            query = query.filter(StatQueue.tenant_uuid.in_(tenant_uuids))
        elif not tenant_uuids and tenant_uuids is not None:
            query = query.filter(text('false'))

        if from_:
            query = query.filter(table.time >= from_)

        if until:
            query = query.filter(table.time < until)

        tz_offset = '+00:00'
        if from_:
            tz_offset = self._extract_timezone_to_postgres_format(from_)

        if start_time and end_time:
            hour = func.extract(
                'HOUR', table.time.op('AT TIME ZONE INTERVAL')(tz_offset)
            )
            query = query.filter(hour.between(start_time, end_time))

        if week_days:
            day_of_week = func.extract(
                'ISODOW', table.time.op('AT TIME ZONE INTERVAL')(tz_offset)
            )
            query = query.filter(day_of_week.in_(week_days))
        elif not week_days and week_days is not None:
            query = query.filter(text('false'))

        return query

    def _queue_stat_query(self, session, **filters):
        query = (
            session.query(
                # NOTE(fblackburn): func.min is a hack to only take one value
                func.min(StatQueue.queue_id).label('queue_id'),
                func.min(StatQueue.name).label('queue_name'),
                func.min(StatQueuePeriodic.time).label('from'),
                func.max(StatQueuePeriodic.time).label('until'),
                func.min(StatQueue.tenant_uuid).label('tenant_uuid'),
                func.sum(StatQueuePeriodic.answered).label('answered'),
                func.sum(StatQueuePeriodic.abandoned).label('abandoned'),
                func.sum(StatQueuePeriodic.total).label('total'),
                func.sum(StatQueuePeriodic.full).label('full'),
                func.sum(StatQueuePeriodic.closed).label('closed'),
                func.sum(StatQueuePeriodic.joinempty).label('joinempty'),
                func.sum(StatQueuePeriodic.leaveempty).label('leaveempty'),
                func.sum(StatQueuePeriodic.divert_ca_ratio).label('divert_ca_ratio'),
                func.sum(StatQueuePeriodic.divert_waittime).label('divert_waittime'),
                func.sum(StatQueuePeriodic.timeout).label('timeout'),
            )
            .select_from(StatQueue)
            .join(StatQueuePeriodic)
            .group_by(StatQueuePeriodic.stat_queue_id)
        )
        query = self._add_interval_query(StatQueuePeriodic, query, **filters)
        return query

    def _get_extra_stats(self, session, stats, **filters):
        answered_on_qos = self._get_answered_on_qos(
            session, stats['queue_id'], **filters
        )
        qos = None
        if stats['answered'] > 0 and answered_on_qos is not None:
            qos = round(100.0 * answered_on_qos / stats['answered'], 2)

        answered_rate_total = (
            stats['answered']
            + stats['abandoned']
            + stats['full']
            + stats['leaveempty']
            + stats['joinempty']
            + stats['timeout']
            + stats['closed']
        )
        answered_rate = None
        if answered_rate_total > 0:
            answered_rate = round(100.0 * stats['answered'] / answered_rate_total, 2)

        total_wait_time = self._get_total_wait_time(
            session, stats['queue_id'], **filters
        )
        waited_call = (
            stats['answered']
            + stats['abandoned']
            + stats['leaveempty']
            + stats['timeout']
        )
        average_waiting_time = None
        if waited_call > 0:
            average_waiting_time = round(float(total_wait_time) / waited_call, 2)

        blocking = stats['joinempty'] + stats['leaveempty']
        saturated = stats['full'] + stats['divert_waittime'] + stats['divert_ca_ratio']

        return {
            'qos': qos,
            'answered_rate': answered_rate,
            'average_waiting_time': average_waiting_time,
            'blocking': blocking,
            'saturated': saturated,
        }

    def _get_answered_on_qos(self, session, queue_id, **filters):
        qos_threshold = filters.get('qos_threshold')
        if qos_threshold is None:
            return

        query = (
            session.query(func.count(StatCallOnQueue.status))
            .filter(StatQueue.queue_id == queue_id)
            .filter(StatCallOnQueue.status == 'answered')
            .filter(StatCallOnQueue.waittime <= qos_threshold)
            .join(StatQueue)
        )
        query = self._add_interval_query(StatCallOnQueue, query, **filters)
        return query.scalar() or 0

    def _get_total_wait_time(self, session, queue_id, **filters):
        query = (
            session.query(func.sum(StatCallOnQueue.waittime))
            .filter(StatQueue.queue_id == queue_id)
            .join(StatQueue)
        )
        query = self._add_interval_query(StatCallOnQueue, query, **filters)
        return query.scalar() or 0
