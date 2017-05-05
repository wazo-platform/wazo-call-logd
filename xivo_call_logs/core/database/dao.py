# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import sqlalchemy as sa

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import exc
from sqlalchemy import sql
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import make_transient
from sqlalchemy.pool import Pool

from xivo_dao.alchemy.call_log import CallLog as CallLogSchema

from xivo_call_logs.core.exceptions import DatabaseServiceUnavailable


# http://stackoverflow.com/questions/34828113/flask-sqlalchemy-losing-connection-after-restarting-of-db-server
@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    del connection_record
    del connection_proxy

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except exc.OperationalError:
        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()


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
        except:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def find_all_in_period(self, start=None, end=None, order=None, direction=None, limit=None, offset=None, search=None, user_uuid=None):
        with self.new_session() as session:
            query = session.query(CallLogSchema)

            if start:
                query = query.filter(CallLogSchema.date >= start)
            if end:
                query = query.filter(CallLogSchema.date < end)

            if search:
                filters = (sql.cast(column, sa.String).ilike('%%%s%%' % search)
                           for column in self.searched_columns)
                query = query.filter(sql.or_(*filters))
            if user_uuid:
                query = query.options(joinedload('participants'))
                query = query.filter(CallLogSchema.participant_user_uuids.contains(str(user_uuid)))

            order_field = None
            if order:
                order_field = getattr(CallLogSchema, order)
            if direction == 'desc':
                order_field = order_field.desc()
            if order_field is not None:
                query = query.order_by(order_field)

            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            call_log_rows = query.all()

            if not call_log_rows:
                return []
            for call_log in call_log_rows:
                make_transient(call_log)
            return call_log_rows

    def count_in_period(self, start=None, end=None, search=None, user_uuid=None):
        with self.new_session() as session:
            query = session.query(CallLogSchema)

            total = query.count()

            if start:
                query = query.filter(CallLogSchema.date >= start)
            if end:
                query = query.filter(CallLogSchema.date < end)
            if search:
                filters = (sql.cast(column, sa.String).ilike('%%%s%%' % search)
                           for column in self.searched_columns)
                query = query.filter(sql.or_(*filters))
            if user_uuid:
                query = query.filter(CallLogSchema.participant_user_uuids.contains(str(user_uuid)))
            filtered = query.count()

        return {'total': total, 'filtered': filtered}
