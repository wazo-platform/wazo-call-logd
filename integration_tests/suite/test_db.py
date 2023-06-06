# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, empty, has_entry
from wazo_test_helpers import until

from .helpers.base import IntegrationTest


class TestDatabase(IntegrationTest):
    def restart_database(self, container_name):
        self.restart_service(container_name, signal='SIGINT')  # fast shutdown
        self.reset_clients()

        db_helper = self.database
        if container_name == 'cel-postgres':
            db_helper = self.cel_database

        until.true(
            db_helper.is_up,
            timeout=5,
            message=f'{container_name} did not come back up',
        )

    def test_query_after_database_restart(self):
        result1 = self.call_logd.cdr.list()

        self.restart_database('cel-postgres')
        self.restart_database('postgres')

        result2 = self.call_logd.cdr.list()

        assert_that(result1, has_entry('items', empty()))
        assert_that(result2, has_entry('items', empty()))
