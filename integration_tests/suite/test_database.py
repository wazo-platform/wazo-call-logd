# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import logging
import os
import random

from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    has_entry,
    has_properties,
    not_,
)

from xivo_test_helpers import until
from xivo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchService,
    NoSuchPort,
)

from wazo_call_logd.database import dao

from .helpers.base import (
    DbHelper,
    IntegrationTest,
    WrongClient,
)
from .helpers.database import call_logs
from .helpers.constants import MASTER_TENANT

logger = logging.getLogger(__name__)
DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}')
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'   # 2019-02-05 21:09:48
NOW = datetime.datetime.now()
MINUTES = datetime.timedelta(minutes=1)
SECONDS = datetime.timedelta(seconds=1)

alice = {
    'exten': '101',
    'context': 'internal',
    'id': 42,
    'line_id': '11',
    'name': 'Alice',
}
bob = {
    'exten': '102',
    'context': 'internal',
    'id': 43,
    'line_id': '22',
    'name': 'Bob',
}
charles = {
    'exten': '103',
    'context': 'internal',
    'id': 44,
    'line_id': '33',
    'name': 'Charles',
}


def cdr(id_=None, caller=None, callee=None, start_time=None, ring_seconds=5, talk_time=30):
    id_ = id_ or random.randint(1, 999999)
    start_time = start_time or NOW
    answer_time = start_time + ring_seconds * SECONDS
    end_time = answer_time + talk_time * SECONDS

    return {
        'id': id_,
        'date': start_time.strftime(TIME_FORMAT),
        'date_answer': answer_time.strftime(TIME_FORMAT),
        'date_end': end_time.strftime(TIME_FORMAT),
        'destination_exten': callee['exten'],
        'destination_name': callee['name'],
        'destination_internal_exten': callee['exten'],
        'destination_internal_context': callee['context'],
        'direction': 'internal',
        'requested_exten': callee['exten'],
        'requested_internal_exten': callee['exten'],
        'requested_internal_context': callee['context'],
        'source_exten': caller['exten'],
        'source_name': caller['name'],
        'source_internal_exten': caller['exten'],
        'source_internal_context': caller['context'],
        'participants': [
            {'user_uuid': caller['id'], 'line_id': caller['line_id'], 'role': 'source'},
            {'user_uuid': callee['id'], 'line_id': caller['line_id'], 'role': 'destination'},
        ],
    }


class TestDatabase(IntegrationTest):
    asset = 'base'

    def restart_postgres(cls):
        cls.restart_service('postgres', signal='SIGINT')  # fast shutdown
        cls.reset_clients()
        until.true(
            cls.database.is_up, timeout=5, message='Postgres did not come back up'
        )

    def test_query_after_database_restart(self):
        result1 = self.call_logd.cdr.list()

        self.restart_postgres()

        result2 = self.call_logd.cdr.list()

        assert_that(result1, has_entry('items', empty()))
        assert_that(result2, has_entry('items', empty()))


class TestDAO(AssetLaunchingTestCase):

    asset = 'database'
    assets_root = os.path.join(os.path.dirname(__file__), '..', 'assets')
    service = 'postgres'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.database = DbHelper.build(
                'asterisk',
                'proformatique',
                'localhost',
                cls.service_port(5432, 'postgres'),
                'asterisk',
            )
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.database = WrongClient(name='database')

    def setUp(self):
        db_uri = DB_URI.format(port=self.service_port(5432, 'postgres'))
        Session = dao.new_db_session(db_uri)
        self.dao = dao.CallLogDAO(Session)

    @call_logs(
        [
            cdr(id_=1, caller=alice, callee=bob, start_time=NOW),
            cdr(id_=2, caller=alice, callee=bob, start_time=NOW + 1 * MINUTES),
            cdr(id_=3, caller=bob, callee=alice, start_time=NOW + 2 * MINUTES),
            cdr(id_=4, caller=alice, callee=charles, start_time=NOW - 5 * MINUTES)
        ]
    )
    def test_that_the_most_recent_call_log_is_returned_for_each_contact(self):
        params = {
            'distinct': 'peer_exten',
        }

        result = self.dao.find_all_in_period(params)
        assert_that(result, contains_inanyorder(
            has_properties(id=3),  # The most recent call between Alice and Bob
            has_properties(id=4),  # The most recent call between Alice and Charles
        ))
