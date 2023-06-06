# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy import and_, distinct, func, sql
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Query, joinedload, subqueryload

from ..models import CallLog, CallLogParticipant
from .base import BaseDAO


class CallLogDAO(BaseDAO):
    searched_columns = (
        CallLog.source_name,
        CallLog.source_exten,
        CallLog.destination_name,
        CallLog.destination_exten,
    )

    def get_by_id(self, cdr_id, tenant_uuids):
        with self.new_session() as session:
            query = session.query(CallLog).options(
                joinedload('participants'),
                joinedload('recordings'),
                subqueryload('source_participant'),
                subqueryload('destination_participant'),
            )
            query = self._apply_filters(query, {'tenant_uuids': tenant_uuids})
            query = query.filter(CallLog.id == cdr_id)
            cdr = query.one_or_none()
            if cdr:
                session.expunge_all()
                return cdr

    def find_all_in_period(self, params):
        with self.new_session() as session:
            query = self._list_query(session, params)
            order_field = None
            if params.get('order'):
                if params['order'] == 'marshmallow_duration':
                    order_field = CallLog.date_end - CallLog.date_answer
                elif params['order'] == 'marshmallow_answered':
                    order_field = CallLog.date_answer
                else:
                    order_field = getattr(CallLog, params['order'])
            if params.get('direction') == 'desc':
                order_field = order_field.desc().nullslast()
            if params.get('direction') == 'asc':
                order_field = order_field.asc().nullsfirst()
            if order_field is not None:
                query = query.order_by(order_field)

            if params.get('limit'):
                query = query.limit(params['limit'])
            if params.get('offset'):
                query = query.offset(params['offset'])

            call_log_rows = query.all()

            if not call_log_rows:
                return []

            session.expunge_all()

            return call_log_rows

    def _list_query(self, session, params):
        distinct_ = params.get('distinct')
        if distinct_ == 'peer_exten':
            # TODO(pcm) use the most recent call log not the most recent id
            sub_query = (
                session.query(func.max(CallLogParticipant.call_log_id).label('max_id'))
                .group_by(CallLogParticipant.user_uuid, CallLogParticipant.peer_exten)
                .subquery()
            )

            query = session.query(CallLog).join(
                sub_query, and_(CallLog.id == sub_query.c.max_id)
            )
        else:
            query = session.query(CallLog)

        query = query.options(
            joinedload('participants'),
            joinedload('recordings'),
            subqueryload('source_participant'),
            subqueryload('destination_participant'),
        )

        query = self._apply_user_filter(query, params)
        query = self._apply_filters(query, params)
        return query

    def count_in_period(self, params):
        with self.new_session() as session:
            query = session.query(CallLog)
            query = self._apply_user_filter(query, params)

            segregation_fields = ('tenant_uuids', 'me_user_uuid')
            count_params = {p: params.get(p) for p in segregation_fields}
            query = self._apply_filters(query, count_params)

            total = query.count()

            session.expunge_all()

            subquery = self._list_query(session, params).subquery()
            filtered = session.query(func.count(distinct(subquery.c.id))).scalar()

        return {'total': total, 'filtered': filtered}

    def _apply_user_filter(self, query: Query, params: dict[str, Any]) -> Query:
        if me_user_uuid := params.get('me_user_uuid'):
            query = query.filter(
                CallLog.participants.any(
                    CallLogParticipant.user_uuid == str(me_user_uuid)
                )
            )
        return query

    def _apply_filters(self, query: Query, params: dict[str, Any]) -> Query:
        if start_date := params.get('start'):
            query = query.filter(CallLog.date >= start_date)
        if end_date := params.get('end'):
            query = query.filter(CallLog.date < end_date)

        if call_direction := params.get('call_direction'):
            query = query.filter(CallLog.direction == call_direction)

        if cdr_ids := params.get('cdr_ids'):
            query = query.filter(CallLog.id.in_(cdr_ids))

        if call_log_id := params.get('id'):
            query = query.filter(CallLog.id == call_log_id)

        if search := params.get('search'):
            filters = (
                sql.cast(column, sa.String).ilike(f'%{search}%')
                for column in self.searched_columns
            )
            query = query.filter(sql.or_(*filters))

        if number := params.get('number'):
            filters = (
                sql.cast(column, sa.String).like(f"{number.replace('_', '%')}")
                for column in [
                    CallLog.source_exten,
                    CallLog.destination_exten,
                ]
            )
            query = query.filter(sql.or_(*filters))

        for tag in params.get('tags', []):
            query = query.filter(
                CallLog.participants.any(
                    CallLogParticipant.tags.contains(sql.cast([tag], ARRAY(sa.String)))
                )
            )

        if tenant_uuids := params.get('tenant_uuids'):
            query = query.filter(CallLog.tenant_uuid.in_(tenant_uuids))

        if me_user_uuid := params.get('me_user_uuid'):
            query = query.filter(
                CallLog.participants.any(
                    CallLogParticipant.user_uuid == str(me_user_uuid)
                )
            )

        if user_uuids := params.get('user_uuids'):
            filters = (
                CallLog.participants.any(CallLogParticipant.user_uuid == str(user_uuid))
                for user_uuid in user_uuids
            )
            query = query.filter(sql.or_(*filters))

        if start_id := params.get('start_id'):
            query = query.filter(CallLog.id >= start_id)

        if (recorded := params.get('recorded')) is not None:
            if recorded:
                query = query.filter(CallLog.recordings.any())
            else:
                query = query.filter(~CallLog.recordings.any())

        return query

    def create_from_list(self, call_logs):
        if not call_logs:
            return

        with self.new_session() as session:
            for call_log in call_logs:
                session.add(call_log)
                session.flush()
                # NOTE(fblackburn): fetch relationship before expunge_all
                call_log.recordings
                call_log.source_participant
                call_log.destination_participant
            session.expunge_all()

    def delete_from_list(self, call_log_ids):
        with self.new_session() as session:
            query = session.query(CallLog)
            query = query.filter(CallLog.id.in_(call_log_ids))
            query.delete(synchronize_session=False)

    def delete(self, older=None):
        with self.new_session() as session:
            query = session.query(CallLog)
            if older:
                query = query.filter(CallLog.date >= older)
            query.delete()
