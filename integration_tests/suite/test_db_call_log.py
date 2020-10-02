# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_inanyorder,
    has_entries,
    has_properties,
)

from .helpers.base import cdr, DBIntegrationTest
from .helpers.database import call_logs
from .helpers.constants import ALICE, BOB, CHARLES, NOW, MINUTES


class TestCallLog(DBIntegrationTest):
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

        result = self.dao.call_log.find_all_in_period(params)
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

        result = self.dao.call_log.count_in_period(params)
        assert_that(result, has_entries(total=4, filtered=2))
