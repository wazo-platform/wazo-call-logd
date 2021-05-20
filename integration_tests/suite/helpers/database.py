# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timedelta as td,
)
from functools import wraps
import logging
import sqlalchemy as sa

from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from xivo_dao.alchemy.stat_agent import StatAgent
from xivo_dao.alchemy.stat_agent_periodic import StatAgentPeriodic
from xivo_dao.alchemy.stat_call_on_queue import StatCallOnQueue
from xivo_dao.alchemy.stat_queue import StatQueue
from xivo_dao.alchemy.stat_queue_periodic import StatQueuePeriodic

from wazo_call_logd.database.models import (
    CallLog,
    CallLogParticipant,
    Export,
    Recording,
    Retention,
)

from .constants import MASTER_TENANT, USER_1_UUID

logger = logging.getLogger(__name__)


def call_logs(number, participant_user=None):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            call_log_ids = []
            for _ in range(number):
                call_log = {'tenant_uuid': MASTER_TENANT}
                with self.database.queries() as queries:
                    call_log_id = queries.insert_call_log(**call_log)
                    if participant_user:
                        participant = {
                            'user_uuid': participant_user,
                            'call_log_id': call_log_id,
                        }
                        queries.insert_call_log_participant(**participant)
                    call_log_ids.append(call_log_id)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.database.queries() as queries:
                    for call_log_id in call_log_ids:
                        queries.delete_call_log(call_log_id)

        return wrapped_function

    return _decorate


def call_log(**call_log):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            recordings = call_log.pop('recordings', [])
            participants = call_log.pop('participants', [])
            call_log.setdefault('tenant_uuid', MASTER_TENANT)
            with self.database.queries() as queries:
                call_log['id'] = queries.insert_call_log(**call_log)
                call_log['participants'] = participants
                for participant in participants:
                    participant['call_log_id'] = call_log['id']
                    queries.insert_call_log_participant(**participant)
                for recording in recordings:
                    recording.setdefault('start_time', dt.utcnow() - td(hours=1))
                    recording.setdefault('end_time', dt.utcnow())
                    recording['call_log_id'] = call_log['id']
                    queries.insert_recording(**recording)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.database.queries() as queries:
                    queries.delete_call_log(call_log['id'])
                    queries.delete_recording_by_call_log_id(call_log['id'])

        return wrapped_function

    return _decorate


def export(**export):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            export.setdefault('date', dt.utcnow())
            export.setdefault('tenant_uuid', MASTER_TENANT)
            export.setdefault('user_uuid', USER_1_UUID)
            with self.database.queries() as queries:
                export['uuid'] = queries.insert_export(**export)
            try:
                return func(self, *args, export, **kwargs)
            finally:
                with self.database.queries() as queries:
                    queries.delete_export(export['uuid'])

        return wrapped_function

    return _decorate


def recording(**recording):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            recording.setdefault('start_time', dt.utcnow() - td(hours=1))
            recording.setdefault('end_time', dt.utcnow())
            recording.setdefault('call_log_id', 42)
            with self.database.queries() as queries:
                recording['uuid'] = queries.insert_recording(**recording)
            try:
                return func(self, *args, recording, **kwargs)
            finally:
                with self.database.queries() as queries:
                    queries.delete_recording(recording['uuid'])

        return wrapped_function

    return _decorate


def retention(**retention):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            retention.setdefault('tenant_uuid', MASTER_TENANT)
            with self.database.queries() as queries:
                queries.insert_retention(**retention)
            try:
                return func(self, *args, retention, **kwargs)
            finally:
                with self.database.queries() as queries:
                    queries.delete_retention(retention['tenant_uuid'])

        return wrapped_function

    return _decorate


def stat_queue(queue):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                queue.setdefault('tenant_uuid', MASTER_TENANT)
                queue.setdefault('name', 'queue')
                queue.setdefault('queue_id', 1)
                queue.setdefault('id', queue['queue_id'])
                queries.insert_stat_queue(**queue)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.cel_database.queries() as queries:
                    queries.delete_stat_queue(queue['id'])

        return wrapped_function

    return _decorate


def stat_agent(agent):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                agent.setdefault('tenant_uuid', MASTER_TENANT)
                agent.setdefault('name', 'agent')
                agent.setdefault('agent_id', 1)
                agent.setdefault('id', agent['agent_id'])
                queries.insert_stat_agent(**agent)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.cel_database.queries() as queries:
                    queries.delete_stat_agent(agent['id'])

        return wrapped_function

    return _decorate


def stat_agent_periodic(stat):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                stat.setdefault('time', '2020-10-01 14:00:00')
                agent_id = stat.pop('agent_id', 1)
                stat['stat_agent_id'] = agent_id
                stat['id'] = queries.insert_stat_agent_periodic(**stat)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.cel_database.queries() as queries:
                    queries.delete_stat_agent_periodic(stat['id'])

        return wrapped_function

    return _decorate


def stat_queue_periodic(stat):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                stat.setdefault('time', '2020-10-01 14:00:00')
                tenant_uuid = stat.pop('tenant_uuid', MASTER_TENANT)
                queue_id = stat.pop('queue_id', 1)
                stat['stat_queue_id'] = queue_id
                queue_args = {
                    'id': stat['stat_queue_id'],
                    'name': 'queue',
                    'tenant_uuid': tenant_uuid,
                    'queue_id': queue_id,
                }
                queries.insert_stat_queue(**queue_args)
                stat['id'] = queries.insert_stat_queue_periodic(**stat)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.cel_database.queries() as queries:
                    queries.delete_stat_queue_periodic(stat['id'])
                    queries.delete_stat_queue(stat['stat_queue_id'])

        return wrapped_function

    return _decorate


def stat_call_on_queue(call):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                call.setdefault('callid', '123')
                call.setdefault('status', 'answered')
                tenant_uuid = call.pop('tenant_uuid', MASTER_TENANT)
                agent_id = call.pop('agent_id', None)
                if agent_id:
                    call['stat_agent_id'] = agent_id
                queue_id = call.pop('queue_id', 1)
                call['stat_queue_id'] = queue_id
                queue_args = {
                    'id': call['stat_queue_id'],
                    'name': 'queue',
                    'tenant_uuid': tenant_uuid,
                    'queue_id': queue_id,
                }
                queries.insert_stat_queue(**queue_args)
                call['id'] = queries.insert_stat_call_on_queue(**call)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.cel_database.queries() as queries:
                    queries.delete_stat_call_on_queue(call['id'])
                    queries.delete_stat_queue(call['stat_queue_id'])

        return wrapped_function

    return _decorate


def cel(**cel):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cel_database.queries() as queries:
                cel.setdefault('eventtype', 'eventtype')
                cel.setdefault('eventtime', dt.now())
                cel.setdefault('uniqueid', 'uniqueid')
                cel.setdefault('linkedid', 'linkedid')
                if cel.pop('processed', False):
                    cel['call_log_id'] = 1
                cel['id'] = queries.insert_cel(**cel)
            try:
                return func(self, *args, cel, **kwargs)
            finally:
                with self.cel_database.queries() as cel_queries:
                    cel_queries.delete_cel(cel['id'])

        return wrapped_function

    return _decorate


class DbHelper:
    @classmethod
    def build(cls, user, password, host, port, db):
        tpl = "postgresql://{user}:{password}@{host}:{port}"
        uri = tpl.format(user=user, password=password, host=host, port=port)
        return cls(uri, db)

    def __init__(self, uri, db):
        self.uri = uri
        self.db = db
        uri = "{}/{}".format(self.uri, self.db)
        self._engine = sa.create_engine(uri, pool_pre_ping=True)

    def is_up(self):
        try:
            self.connect()
            return True
        except Exception as e:
            logger.debug('Database is down: %s', e)
            return False

    def connect(self):
        return self._engine.connect()

    def execute(self, query, **kwargs):
        with self.connect() as connection:
            connection.execute(text(query), **kwargs)

    @contextmanager
    def queries(self):
        with self.connect() as connection:
            yield DatabaseQueries(connection)


class DatabaseQueries:
    def __init__(self, connection):
        self.connection = connection
        self.Session = scoped_session(sessionmaker(bind=connection))

    def insert_call_log(self, **kwargs):
        session = self.Session()
        kwargs.setdefault('date', dt.now())
        kwargs.setdefault('tenant_uuid', MASTER_TENANT)
        call_log = CallLog(**kwargs)
        session.add(call_log)
        session.flush()
        call_log_id = call_log.id
        session.commit()
        return call_log_id

    def delete_call_log(self, call_log_id):
        session = self.Session()
        session.query(CallLog).filter(CallLog.id == call_log_id).delete()
        session.commit()

    def insert_export(self, **kwargs):
        session = self.Session()
        kwargs.setdefault('date', dt.now())
        kwargs.setdefault('tenant_uuid', MASTER_TENANT)
        export = Export(**kwargs)
        session.add(export)
        session.flush()
        export_uuid = export.uuid
        session.commit()
        return export_uuid

    def delete_export(self, export_uuid):
        session = self.Session()
        session.query(Export).filter(Export.uuid == export_uuid).delete()
        session.commit()

    def insert_recording(self, **kwargs):
        session = self.Session()
        recording = Recording(**kwargs)
        session.add(recording)
        session.flush()
        recording_uuid = recording.uuid
        session.commit()
        return recording_uuid

    def delete_recording(self, recording_uuid):
        session = self.Session()
        session.query(Recording).filter(Recording.uuid == recording_uuid).delete()
        session.commit()

    def insert_retention(self, **kwargs):
        session = self.Session()
        retention = Retention(**kwargs)
        session.add(retention)
        session.commit()

    def delete_retention(self, tenant_uuid):
        session = self.Session()
        query = session.query(Retention)
        query = query.filter(Retention.tenant_uuid == tenant_uuid)
        query.delete()
        session.commit()

    def delete_recording_by_call_log_id(self, call_log_id):
        session = self.Session()
        session.query(Recording).filter(Recording.call_log_id == call_log_id).delete()
        session.commit()

    def clear_call_logs(self):
        session = self.Session()
        session.query(CallLog).delete()
        session.commit()

    def clear_recordings(self):
        session = self.Session()
        session.query(Recording).delete()
        session.commit()

    def insert_call_log_participant(self, **kwargs):
        session = self.Session()
        kwargs.setdefault('role', 'source')
        call_log_participant = CallLogParticipant(**kwargs)
        session.add(call_log_participant)
        session.commit()

    def find_all_call_log(self):
        session = self.Session()
        call_logs = session.query(CallLog).order_by(CallLog.date).all()
        session.commit()
        return call_logs

    def find_last_call_log(self):
        session = self.Session()
        call_log = session.query(CallLog).order_by(CallLog.date).first()
        session.commit()
        if call_log:
            call_log.tenant_uuid = str(call_log.tenant_uuid)
            if call_log.destination_user_uuid:
                call_log.destination_user_uuid = str(call_log.destination_user_uuid)
            if call_log.source_user_uuid:
                call_log.source_user_uuid = str(call_log.source_user_uuid)
        return call_log

    def find_all_recordings(self, call_log_id):
        session = self.Session()
        query = session.query(Recording).filter(Recording.call_log_id == call_log_id)
        recordings = query.all()
        session.commit()
        return recordings

    def get_call_log_user_uuids(self, call_log_id):
        session = self.Session()
        call_log = session.query(CallLog).filter(CallLog.id == call_log_id).first()
        result = tuple(call_log.participant_user_uuids)
        session.commit()
        return result

    def get_call_log_tenant_uuids(self, call_log_id):
        session = self.Session()
        call_log = session.query(CallLog).filter(CallLog.id == call_log_id).first()
        session.commit()
        return call_log.tenant_uuid

    def insert_cel(self, **kwargs):
        kwargs.setdefault('userdeftype', '')
        kwargs.setdefault('cid_name', 'default name')
        kwargs.setdefault('cid_num', '9999')
        kwargs.setdefault('cid_ani', '')
        kwargs.setdefault('cid_rdnis', '')
        kwargs.setdefault('cid_dnid', '')
        kwargs.setdefault('exten', '')
        kwargs.setdefault('context', '')
        kwargs.setdefault('channame', '')
        kwargs.setdefault('appname', '')
        kwargs.setdefault('appdata', '')
        kwargs.setdefault('amaflags', 0)
        kwargs.setdefault('accountcode', '')
        kwargs.setdefault('peeraccount', '')
        kwargs.setdefault('userfield', '')
        kwargs.setdefault('peer', '')

        # NOTE(flackburn): remove empty string value
        if not kwargs.get('call_log_id'):
            kwargs['call_log_id'] = None
        if not kwargs.get('extra'):
            kwargs['extra'] = None

        query = text(
            """
        INSERT INTO cel (
            eventtype,
            eventtime,
            uniqueid,
            linkedid,
            userdeftype,
            cid_name,
            cid_num,
            cid_ani,
            cid_rdnis,
            cid_dnid,
            exten,
            context,
            channame,
            appname,
            appdata,
            amaflags,
            accountcode,
            peeraccount,
            userfield,
            peer,
            call_log_id,
            extra
        )
        VALUES (
            :eventtype,
            :eventtime,
            :uniqueid,
            :linkedid,
            :userdeftype,
            :cid_name,
            :cid_num,
            :cid_ani,
            :cid_rdnis,
            :cid_dnid,
            :exten,
            :context,
            :channame,
            :appname,
            :appdata,
            :amaflags,
            :accountcode,
            :peeraccount,
            :userfield,
            :peer,
            :call_log_id,
            :extra
        )
        RETURNING id
        """
        )

        cel_id = self.connection.execute(query, **kwargs).scalar()
        return cel_id

    def delete_cel(self, cel_id):
        query = text("DELETE FROM cel WHERE id = :id")
        self.connection.execute(query, id=cel_id)

    def insert_stat_agent(self, **kwargs):
        session = self.Session()
        agent = StatAgent(**kwargs)
        session.add(agent)
        session.flush()
        stat_agent_id = agent.id
        session.commit()
        return stat_agent_id

    def delete_stat_agent(self, stat_agent_id):
        session = self.Session()
        query = session.query(StatCallOnQueue).filter(
            StatCallOnQueue.stat_agent_id == stat_agent_id
        )
        if not query.count() > 0:
            session.query(StatAgent).filter(StatAgent.id == stat_agent_id).delete()
        session.commit()

    def insert_stat_agent_periodic(self, **kwargs):
        session = self.Session()
        stat = StatAgentPeriodic(**kwargs)
        session.add(stat)
        session.flush()
        # NOTE(fblackburn) Avoid BEGIN new session after commit
        stat_id = stat.id
        session.commit()
        return stat_id

    def delete_stat_agent_periodic(self, stat_id):
        session = self.Session()
        session.query(StatAgentPeriodic).filter(
            StatAgentPeriodic.id == stat_id
        ).delete()
        session.commit()

    def insert_stat_queue_periodic(self, **kwargs):
        session = self.Session()
        stat = StatQueuePeriodic(**kwargs)
        session.add(stat)
        session.flush()
        # NOTE(fblackburn) Avoid BEGIN new session after commit
        stat_id = stat.id
        session.commit()
        return stat_id

    def delete_stat_queue_periodic(self, stat_id):
        session = self.Session()
        session.query(StatQueuePeriodic).filter(
            StatQueuePeriodic.id == stat_id
        ).delete()
        session.commit()

    def insert_stat_call_on_queue(self, **kwargs):
        session = self.Session()
        call = StatCallOnQueue(**kwargs)
        session.add(call)
        session.flush()
        # NOTE(fblackburn) Avoid BEGIN new session after commit
        call_id = call.id
        session.commit()
        return call_id

    def delete_stat_call_on_queue(self, call_id):
        session = self.Session()
        session.query(StatCallOnQueue).filter(StatCallOnQueue.id == call_id).delete()
        session.commit()

    def insert_stat_queue(self, **kwargs):
        session = self.Session()
        queue_id = kwargs['id']
        query = session.query(StatQueue).filter(StatQueue.id == queue_id)
        if not query.count() > 0:
            queue = StatQueue(**kwargs)
            session.add(queue)
        session.commit()

    def delete_stat_queue(self, stat_queue_id):
        session = self.Session()
        query_1 = session.query(StatQueuePeriodic).filter(
            StatQueuePeriodic.stat_queue_id == stat_queue_id
        )
        query_2 = session.query(StatCallOnQueue).filter(
            StatCallOnQueue.stat_queue_id == stat_queue_id
        )
        if not query_1.count() > 0 and not query_2.count() > 0:
            session.query(StatQueue).filter(StatQueue.id == stat_queue_id).delete()
        session.commit()
