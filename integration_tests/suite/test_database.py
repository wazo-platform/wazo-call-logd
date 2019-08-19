# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os

from hamcrest import (
    assert_that,
    empty,
    has_entry,
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
            {
                'id': 12,
                'date': '2017-03-23 00:00:00',
                'date_answer': '2017-03-23 00:01:00',
                'date_end': '2017-03-23 00:02:27',
                'destination_exten': '3378',
                'destination_name': 'dést,ination',
                'destination_internal_exten': '3245',
                'destination_internal_context': 'internal',
                'direction': 'internal',
                'requested_exten': '3958',
                'requested_internal_exten': '3490',
                'requested_internal_context': 'internal',
                'source_exten': '7687',
                'source_name': 'soùr.',
                'source_internal_exten': '5938',
                'source_internal_context': 'internal',
                'participants': [
                    {
                        'user_uuid': 42,
                        'line_id': '11',
                        'tags': ['rh', 'Poudlard'],
                        'role': 'source',
                    },
                    {'user_uuid': 43, 'line_id': '22', 'role': 'destination'},
                ],
            }
        ]
    )
    def test_get_by_id(self):
        # TODO remove this test it was added to test the DB test boilerplate
        result = self.dao.get_by_id(12, [MASTER_TENANT])

        assert_that(result, not_(None))
