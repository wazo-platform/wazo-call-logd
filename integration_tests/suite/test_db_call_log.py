# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timedelta as td,
)
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    has_entries,
    has_length,
    empty,
    has_property,
    has_properties,
)
from wazo_call_logd.database.models import CallLog, CallLogParticipant, Recording

from .helpers.base import cdr, DBIntegrationTest
from .helpers.database import recording, call_log
from .helpers.constants import (
    ALICE,
    BOB,
    CHARLES,
    MASTER_TENANT,
    MINUTES,
    NOW,
    USER_1_UUID,
)


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

    @call_log(**{'id': 1})
    @recording(call_log_id=1, start_time=NOW + 2 * MINUTES)
    @recording(call_log_id=1, start_time=NOW + 1 * MINUTES)
    def test_that_recordings_order_is_by_start_time(self, rec1, rec2):
        params = {}
        result = self.dao.call_log.find_all_in_period(params)
        assert_that(
            result[0].recordings,
            contains_exactly(
                has_properties(uuid=rec2['uuid']),
                has_properties(uuid=rec1['uuid']),
            ),
        )

    @call_log(**{'id': 1})
    @call_log(**{'id': 2})
    @recording(call_log_id=1)
    def test_that_recordings_filter_shows_only_filtered_calls(self, rec1):
        params = {'recorded': True}
        result = self.dao.call_log.find_all_in_period(params)
        assert_that(
            result,
            contains_exactly(
                has_properties(
                    id=1,
                    recordings=contains_exactly(has_properties(uuid=rec1['uuid'])),
                ),
            ),
        )
        params = {'recorded': False}
        result = self.dao.call_log.find_all_in_period(params)
        assert_that(
            result,
            contains_exactly(
                has_properties(
                    id=2,
                    recordings=empty(),
                ),
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

    @call_log(**cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW))
    @call_log(**cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES))
    @call_log(**cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES))
    @call_log(**cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES))
    def test_find_from_cdr_ids_list(self):
        params = {'cdr_ids': [1, 2]}
        results = self.dao.call_log.find_all_in_period(params)
        assert_that(
            results,
            contains_inanyorder(
                has_properties(id=1),
                has_properties(id=2),
            )
        )

        params = {'cdr_ids': [1, 42, 3]}
        results = self.dao.call_log.find_all_in_period(params)
        assert_that(
            results,
            contains_inanyorder(
                has_properties(id=1),
                has_properties(id=3),
            )
        )

        params = {'cdr_ids': [42]}
        results = self.dao.call_log.find_all_in_period(params)
        assert_that(results, empty())

        params = {'cdr_ids': []}
        results = self.dao.call_log.find_all_in_period(params)
        assert_that(
            results,
            contains_inanyorder(
                has_properties(id=1),
                has_properties(id=2),
                has_properties(id=3),
                has_properties(id=4),
            )
        )

    def test_create_from_list(self):
        end_time = dt.now()
        start_time = end_time - td(hours=1)

        call_log_1 = CallLog(
            date=NOW,
            tenant_uuid=MASTER_TENANT,
            participants=[CallLogParticipant(role='source', user_uuid=USER_1_UUID)],
            recordings=[
                Recording(start_time=start_time, end_time=end_time),
                Recording(start_time=start_time, end_time=end_time),
            ],
        )
        call_log_2 = CallLog(date=NOW, tenant_uuid=MASTER_TENANT)

        self.dao.call_log.create_from_list([call_log_1, call_log_2])

        result = self.session.query(CallLog).all()
        assert_that(result, has_length(2))

        result = self.session.query(CallLogParticipant).all()
        assert_that(result, has_length(1))

        result = self.session.query(Recording).all()
        assert_that(result, has_length(2))

        self.session.query(CallLog).delete()
        self.session.query(CallLogParticipant).delete()
        self.session.query(Recording).delete()
        self.session.commit()

    @call_log(**cdr(id_=1))
    @call_log(**cdr(id_=2))
    @call_log(**cdr(id_=3))
    def test_delete_from_list(self):
        id_1, id_2, id_3 = [1, 2, 3]
        self.dao.call_log.delete_from_list([id_1, id_3])

        result = self.session.query(CallLog).all()
        assert_that(result, contains_exactly(has_property('id', id_2)))

    @call_log(**cdr(id_=1))
    @call_log(**cdr(id_=2))
    @call_log(**cdr(id_=3))
    def test_delete_all(self):
        self.dao.call_log.delete()

        result = self.session.query(CallLog).all()
        assert_that(result, empty())

    @call_log(**cdr(id_=1, start_time=NOW))
    @call_log(**cdr(id_=2, start_time=NOW - td(hours=2)))  # excluded
    @call_log(**cdr(id_=3, start_time=NOW))
    def test_delete_older(self):
        older = NOW - td(hours=1)
        self.dao.call_log.delete(older=older)

        result = self.session.query(CallLog).all()
        assert_that(result, contains_exactly(has_property('id', 2)))
