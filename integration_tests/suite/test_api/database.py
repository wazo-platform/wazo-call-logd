# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

import sqlalchemy as sa

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
