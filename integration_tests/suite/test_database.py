# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from hamcrest import assert_that
from hamcrest import empty
from hamcrest import has_entry

from xivo_test_helpers import until

from .test_api.base import IntegrationTest

logger = logging.getLogger(__name__)


class TestDatabase(IntegrationTest):
    asset = 'base'

    def restart_postgres(self):
        self.restart_service('postgres')
        self.reset_clients()
        until.true(self.database.is_up, tries=5)

    def test_query_after_database_restart(self):
        result1 = self.call_logd.cdr.list()

        self.restart_postgres()

        result2 = self.call_logd.cdr.list()

        assert_that(result1, has_entry('items', empty()))
        assert_that(result2, has_entry('items', empty()))
