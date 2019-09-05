# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os

from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    has_entry,
    has_entries,
    has_properties,
)

from xivo_test_helpers import until
from xivo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchService,
    NoSuchPort,
)

from wazo_call_logd.database import dao

from .helpers.base import cdr, DbHelper, IntegrationTest, WrongClient
from .helpers.database import call_logs
from .helpers.constants import ALICE, BOB, CHARLES, NOW, MINUTES

logger = logging.getLogger(__name__)
DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}')


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
            cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW),
            cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES),
            cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES),
            cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES),
        ]
    )
    def test_that_the_most_recent_call_log_is_returned_for_each_contact(self):
        params = {'distinct': 'peer_exten'}

        result = self.dao.find_all_in_period(params)
        assert_that(
            result,
            contains_inanyorder(
                has_properties(id=3),  # The most recent call between Alice and Bob
                has_properties(id=4),  # The most recent call between Alice and Charles
            ),
        )

    @call_logs(
        [
            cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW),
            cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES),
            cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES),
            cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES),
        ]
    )
    def test_count_distinct(self):
        params = {'distinct': 'peer_exten'}

        result = self.dao.count_in_period(params)
        assert_that(result, has_entries(total=4, filtered=2))
