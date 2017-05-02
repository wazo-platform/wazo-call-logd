# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import sqlalchemy as sa
import uuid

from contextlib import contextmanager
from datetime import timedelta
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


class DbHelper(object):

    TEMPLATE = "xivotemplate"

    @classmethod
    def build(cls, user, password, host, port, db):
        tpl = "postgresql://{user}:{password}@{host}:{port}"
        uri = tpl.format(user=user,
                         password=password,
                         host=host,
                         port=port)
        return cls(uri, db)

    def __init__(self, uri, db):
        self.uri = uri
        self.db = db

    def is_up(self):
        try:
            self.connect()
            return True
        except Exception as e:
            logger.debug('Database is down: %s', e)
            return False

    def create_engine(self, db=None, isolate=False):
        db = db or self.db
        uri = "{}/{}".format(self.uri, db)
        if isolate:
            return sa.create_engine(uri, isolation_level='AUTOCOMMIT')
        return sa.create_engine(uri)

    def connect(self, db=None):
        db = db or self.db
        return self.create_engine(db).connect()

    def recreate(self):
        engine = self.create_engine("postgres", isolate=True)
        connection = engine.connect()
        connection.execute("""
                           SELECT pg_terminate_backend(pg_stat_activity.pid)
                           FROM pg_stat_activity
                           WHERE pg_stat_activity.datname = '{db}'
                           AND pid <> pg_backend_pid()
                           """.format(db=self.db))
        connection.execute("DROP DATABASE IF EXISTS {db}".format(db=self.db))
        connection.execute("CREATE DATABASE {db} TEMPLATE {template}".format(db=self.db,
                                                                             template=self.TEMPLATE))
        connection.close()

    def execute(self, query, **kwargs):
        with self.connect() as connection:
            connection.execute(text(query), **kwargs)

    @contextmanager
    def queries(self):
        with self.connect() as connection:
            yield DatabaseQueries(connection)


class DatabaseQueries(object):

    def __init__(self, connection):
        self.connection = connection

    def insert_call_log(
            self,
            date,
            source_name='source',
            source_exten='1111',
            destination_name='destination',
            destination_exten='2222',
            duration=timedelta(seconds=1),
            user_field='',
            answered=True,
            source_line_identity='sip/source',
            destination_line_identity='sip/destination',
    ):
        query = text("""
        INSERT INTO call_log (
            date,
            source_name,
            source_exten,
            destination_name,
            destination_exten,
            duration,
            user_field,
            answered,
            source_line_identity,
            destination_line_identity
        )
        VALUES (
            :date,
            :source_name,
            :source_exten,
            :destination_name,
            :destination_exten,
            :duration,
            :user_field,
            :answered,
            :source_line_identity,
            :destination_line_identity
        )
        RETURNING id
        """)

        call_log_id = (self.connection
                       .execute(query,
                                date=date,
                                source_name=source_name,
                                source_exten=source_exten,
                                destination_name=destination_name,
                                destination_exten=destination_exten,
                                duration=duration,
                                user_field=user_field,
                                answered=answered,
                                source_line_identity=source_line_identity,
                                destination_line_identity=destination_line_identity)
                       .scalar())
        return call_log_id

    def delete_call_log(self, call_log_id):
        query = text("DELETE FROM call_log WHERE id = :id")
        self.connection.execute(query, id=call_log_id)

    def insert_call_log_participant(self, call_log_id, user_uuid, line_id=None):
        uuid_ = str(uuid.uuid4())
        query = text("""
        INSERT INTO call_log_participant (
            uuid,
            call_log_id,
            user_uuid,
            line_id
        )
        VALUES (
            :uuid,
            :call_log_id,
            :user_uuid,
            :line_id
        )
        """)
        self.connection.execute(query,
                                uuid=uuid_,
                                call_log_id=call_log_id,
                                user_uuid=user_uuid,
                                line_id=line_id)

    def insert_cel(
            self,
            eventtype,
            eventtime,
            uniqueid,
            linkedid,
            userdeftype='',
            cid_name='default name',
            cid_num='9999',
            cid_ani='',
            cid_rdnis='',
            cid_dnid='',
            exten='',
            context='',
            channame='',
            appname='',
            appdata='',
            amaflags=0,
            accountcode='',
            peeraccount='',
            userfield='',
            peer='',
            call_log_id=None,
            extra=None,
    ):
        query = text("""
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
        """)

        cel_id = (self.connection
                  .execute(query,
                           eventtype=eventtype,
                           eventtime=eventtime,
                           uniqueid=uniqueid,
                           linkedid=linkedid,
                           userdeftype=userdeftype,
                           cid_name=cid_name,
                           cid_num=cid_num,
                           cid_ani=cid_ani,
                           cid_rdnis=cid_rdnis,
                           cid_dnid=cid_dnid,
                           exten=exten,
                           context=context,
                           channame=channame,
                           appname=appname,
                           appdata=appdata,
                           amaflags=amaflags,
                           accountcode=accountcode,
                           peeraccount=peeraccount,
                           userfield=userfield,
                           peer=peer,
                           call_log_id=call_log_id,
                           extra=extra)
                  .scalar())
        return cel_id

    def delete_cel(self, cel_id):
        query = text("DELETE FROM cel WHERE id = :id")
        self.connection.execute(query, id=cel_id)
