# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import timedelta as td
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    has_entries,
    has_length,
    empty,
    has_property,
    has_properties,
)
from wazo_call_logd.database.models import CallLog

from .helpers.base import cdr, DBIntegrationTest
from .helpers.database import call_log
from .helpers.constants import ALICE, BOB, CHARLES, NOW, MINUTES, MASTER_TENANT


class TestCallLog(DBIntegrationTest):
    @call_log(**cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW))
    @call_log(**cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES))
    @call_log(**cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES))
    @call_log(**cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES))
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

    @call_log(**cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW))
    @call_log(**cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES))
    @call_log(**cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES))
    @call_log(**cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES))
    def test_count_distinct(self):
        params = {'distinct': 'peer_exten'}

        result = self.dao.call_log.count_in_period(params)
        assert_that(result, has_entries(total=4, filtered=2))

    def test_create_from_list(self):
        call_log_1 = CallLog(date=NOW, tenant_uuid=MASTER_TENANT)
        call_log_2 = CallLog(date=NOW, tenant_uuid=MASTER_TENANT)

        self.dao.call_log.create_from_list([call_log_1, call_log_2])

        result = self.session.query(CallLog).all()
        assert_that(result, has_length(2))

        self.session.query(CallLog).delete()
        self.session.commit()

    @call_log(**cdr(id_=1))
    @call_log(**cdr(id_=2))
    @call_log(**cdr(id_=3))
    def test_delete_from_list(self):
        id_1, id_2, id_3 = [1, 2, 3]
        self.dao.call_log.delete_from_list([id_1, id_3])

        result = self.session.query(CallLog).all()
        assert_that(result, contains(has_property('id', id_2)))

    @call_log(**cdr(id_=1))
    @call_log(**cdr(id_=2))
    @call_log(**cdr(id_=3))
    def test_delete_all(self):
        ids_deleted = self.dao.call_log.delete()

        assert_that(ids_deleted, contains_inanyorder(1, 2, 3))
        result = self.session.query(CallLog).all()
        assert_that(result, empty())

    @call_log(**cdr(id_=1, start_time=NOW))
    @call_log(**cdr(id_=2, start_time=NOW - td(hours=2)))  # excluded
    @call_log(**cdr(id_=3, start_time=NOW))
    def test_delete_older(self):
        older = NOW - td(hours=1)
        ids_deleted = self.dao.call_log.delete(older=older)

        assert_that(ids_deleted, contains_inanyorder(1, 3))
        result = self.session.query(CallLog).all()
        assert_that(result, contains(has_property('id', 2)))

    def test_delete_empty(self):
        result = self.dao.call_log.delete()
        assert_that(result, empty())
