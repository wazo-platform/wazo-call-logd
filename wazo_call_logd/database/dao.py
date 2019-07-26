# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager

import sqlalchemy as sa

from sqlalchemy import create_engine
from sqlalchemy import exc
from sqlalchemy import sql
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from xivo import sqlalchemy_helper
from xivo_dao.alchemy.call_log import CallLog as CallLogSchema
from xivo_dao.alchemy.call_log_participant import CallLogParticipant

from wazo_call_logd.exceptions import DatabaseServiceUnavailable


sqlalchemy_helper.handle_db_restart()


def new_db_session(db_uri):
    _Session = scoped_session(sessionmaker())
    engine = create_engine(db_uri)
    _Session.configure(bind=engine)
    return _Session


class CallLogDAO(object):

    searched_columns = (
        CallLogSchema.source_name,
        CallLogSchema.source_exten,
        CallLogSchema.destination_name,
        CallLogSchema.destination_exten,
    )

    def __init__(self, Session):
        self._Session = Session

    @contextmanager
    def new_session(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except exc.OperationalError:
            session.rollback()
            raise DatabaseServiceUnavailable()
        except BaseException:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def get_by_id(self, cdr_id, tenant_uuids):
        with self.new_session() as session:
            query = session.query(CallLogSchema).options(joinedload('participants'),
                                                         subqueryload('source_participant'),
                                                         subqueryload('destination_participant'))
            query = self._apply_filters(query, {'tenant_uuids': tenant_uuids})
            query = query.filter(CallLogSchema.id == cdr_id)
            cdr = query.one_or_none()
            if cdr:
                session.expunge_all()
                return cdr

    def find_all_in_period(self, params):
        with self.new_session() as session:
            query = session.query(CallLogSchema)
            query = query.options(joinedload('participants'),
                                  subqueryload('source_participant'),
                                  subqueryload('destination_participant'))

            query = self._apply_user_filter(query, params)
            query = self._apply_filters(query, params)

            order_field = None
            if params.get('order'):
                if params['order'] == 'marshmallow_duration':
                    order_field = CallLogSchema.date_end - CallLogSchema.date_answer
                elif params['order'] == 'marshmallow_answered':
                    order_field = CallLogSchema.date_answer
                else:
                    order_field = getattr(CallLogSchema, params['order'])
            if params.get('direction') == 'desc':
                order_field = order_field.desc()
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

    def count_in_period(self, params):
        with self.new_session() as session:
            query = session.query(CallLogSchema)
            query = self._apply_user_filter(query, params)

            segregation_fields = ('tenant_uuids', 'me_user_uuid')
            count_params = dict([(p, params.get(p))
                                 for p in segregation_fields])
            query = self._apply_filters(query, count_params)

            total = query.count()

            query = self._apply_filters(query, params)

            filtered = query.count()

        return {'total': total, 'filtered': filtered}

    def _apply_user_filter(self, query, params):
        if params.get('me_user_uuid'):
            me_user_uuid = params['me_user_uuid']
            query = query.filter(CallLogSchema.participant_user_uuids.contains(str(me_user_uuid)))
        return query

    def _apply_filters(self, query, params):
        if params.get('start'):
            query = query.filter(CallLogSchema.date >= params['start'])
        if params.get('end'):
            query = query.filter(CallLogSchema.date < params['end'])

        if params.get('call_direction'):
            query = query.filter(CallLogSchema.direction == params['call_direction'])

        if params.get('search'):
            filters = (sql.cast(column, sa.String).ilike('%%%s%%' % params['search'])
                       for column in self.searched_columns)
            query = query.filter(sql.or_(*filters))

        if params.get('number'):
            sql_regex = params['number'].replace('_', '%')
            filters = (sql.cast(column, sa.String).like('%s' % sql_regex)
                       for column in [CallLogSchema.source_exten, CallLogSchema.destination_exten])
            query = query.filter(sql.or_(*filters))

        for tag in params.get('tags', []):
            query = query.filter(CallLogSchema.participants.any(
                CallLogParticipant.tags.contains(sql.cast([tag], ARRAY(sa.String)))
            ))

        if params.get('tenant_uuids'):
            query = query.filter(CallLogSchema.tenant_uuid.in_(params['tenant_uuids']))

        if params.get('me_user_uuid'):
            me_user_uuid = params['me_user_uuid']
            query = query.filter(CallLogSchema.participant_user_uuids.contains(str(me_user_uuid)))

        if params.get('user_uuids'):
            filters = (CallLogSchema.participant_user_uuids.contains(str(user_uuid))
                       for user_uuid in params['user_uuids'])
            query = query.filter(sql.or_(*filters))

        if params.get('start_id'):
            query = query.filter(CallLogSchema.id >= params['start_id'])

        return query
