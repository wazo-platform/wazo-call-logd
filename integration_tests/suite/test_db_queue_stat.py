# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
)
from .helpers.base import DBIntegrationTest
from .helpers.database import stat_queue_periodic, stat_call_on_queue
from .helpers.constants import OTHER_TENANT, USERS_TENANT

QUEUE_ID = 1


class TestQueueStat(DBIntegrationTest):
    # fmt: off
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-01 14:00:00'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-01 15:00:00'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 14:00:00', 'answered': 2})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 15:00:00', 'answered': 3})
    @stat_call_on_queue({'queue_id': 2, 'time': '2020-10-01 14:00:00'})
    @stat_call_on_queue({'queue_id': 2, 'time': '2020-10-01 15:00:00'})
    @stat_call_on_queue({'queue_id': 2, 'time': '2020-10-01 16:00:00'})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'answered': 4})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 15:00:00', 'answered': 5})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 16:00:00', 'answered': 6})
    # fmt: on
    def test_get_interval_group_by_queues(self):
        tenant_uuids = None
        interval = {
            'from_': '2020-10-01 14:00:00',
            'until': '2020-10-01 16:00:00',
            'qos_threshold': 0,
        }

        result = self.dao.queue_stat.get_interval(tenant_uuids, **interval)
        res1 = 2 + 3
        res2 = 4 + 5
        assert_that(
            result,
            contains_inanyorder(
                has_entries(queue_id=1, answered=res1, qos=self.qos(res1, 2)),
                has_entries(queue_id=2, answered=res2, qos=self.qos(res2, 2)),
            ),
        )

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 14:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 15:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 16:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'answered': 2})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'answered': 3})
    @stat_queue_periodic({'time': '2020-10-01 16:00:00', 'answered': 4})
    def test_get_interval_include_limit(self):
        tenant_uuids = None
        interval = {
            'from_': '2020-10-01 14:00:00',
            'until': '2020-10-01 16:00:00',
            'qos_threshold': 0,
        }

        result = self.dao.queue_stat.get_interval(tenant_uuids, **interval)
        res = 2 + 3
        assert_that(result[0], has_entries(answered=res, qos=self.qos(res, 2)))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 14:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'answered': 2})
    def test_get_interval_without_interval(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids, qos_threshold=0)
        res = 1 + 2
        assert_that(result[0], has_entries(answered=res, qos=self.qos(res, 2)))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 14:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'answered': 2})
    def test_get_interval_without_filters(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids)
        res = 1 + 2
        assert_that(result[0], has_entries(answered=res, qos=None))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 14:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 15:00:00'})
    @stat_call_on_queue({'time': '2020-10-01 16:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'answered': 2})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'answered': 3})
    @stat_queue_periodic({'time': '2020-10-01 16:00:00', 'answered': 4})
    def test_get_interval_with_start_end_time(self):
        tenant_uuids = None
        kwargs = {'start_time': 14, 'end_time': 15, 'qos_threshold': 0}
        result = self.dao.queue_stat.get_interval(tenant_uuids, **kwargs)
        res = 2 + 3
        assert_that(result[0], has_entries(answered=res, qos=self.qos(res, 2)))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-02 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-03 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-04 13:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})  # Thursday
    @stat_queue_periodic({'time': '2020-10-02 13:00:00', 'answered': 2})  # Friday
    @stat_queue_periodic({'time': '2020-10-03 13:00:00', 'answered': 3})  # Saturday
    @stat_queue_periodic({'time': '2020-10-04 13:00:00', 'answered': 4})  # Sunday
    def test_get_interval_with_week_days(self):
        tenant_uuids = None
        kwargs = {'week_days': [1, 2, 3, 4, 5], 'qos_threshold': 0}
        result = self.dao.queue_stat.get_interval(tenant_uuids, **kwargs)
        res = 1 + 2
        assert_that(result[0], has_entries(answered=res, qos=self.qos(res, 2)))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_call_on_queue({'time': '2020-10-02 13:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1})  # Thursday
    @stat_queue_periodic({'time': '2020-10-02 13:00:00', 'answered': 2})  # Friday
    def test_get_interval_with_empty_week_days(self):
        tenant_uuids = None
        kwargs = {'week_days': [], 'qos_threshold': 0}
        result = self.dao.queue_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(result, empty())

    @stat_call_on_queue({'time': '2020-10-01 13:00:00'})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00'})
    def test_get_interval_with_values_to_zero(self):
        tenant_uuids = None
        kwargs = {'qos_threshold': 0}
        result = self.dao.queue_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(
            result[0],
            has_entries(
                qos=None,
                answered_rate=None,
                blocking=0,
                saturated=0,
                average_waiting_time=None
            )
        )

    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 10})
    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 10})
    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 20})
    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 20})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 4})
    def test_get_interval_return_specific_qos(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids, qos_threshold=15)
        expected = round(100.0 * 2 / 4)
        assert_that(result[0], has_entries(qos=expected))

    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 10})
    @stat_call_on_queue({'time': '2020-10-01 13:00:00', 'waittime': 10})
    @stat_call_on_queue({'time': '2020-10-01 14:00:00', 'waittime': 20})
    @stat_call_on_queue({'time': '2020-10-01 15:00:00', 'waittime': 20})
    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1, 'timeout': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'leaveempty': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'abandoned': 1})
    def test_get_interval_return_specific_average_waiting_time(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids)
        assert_that(result[0], has_entries(average_waiting_time=15))

    @stat_queue_periodic({'time': '2020-10-01 13:00:00', 'answered': 1, 'timeout': 1})
    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'leaveempty': 1, 'full': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'abandoned': 1, 'closed': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'joinempty': 1})
    def test_get_interval_return_specific_answered_rate(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids)
        expected = round(100.0 * 1 / 7, 2)
        assert_that(result[0], has_entries(answered_rate=expected))

    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'leaveempty': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'joinempty': 1})
    def test_get_interval_return_specific_blocking(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids)
        assert_that(result[0], has_entries(blocking=2))

    @stat_queue_periodic({'time': '2020-10-01 14:00:00', 'full': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'divert_ca_ratio': 1})
    @stat_queue_periodic({'time': '2020-10-01 15:00:00', 'divert_waittime': 1})
    def test_get_interval_return_specific_saturated(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids)
        assert_that(result[0], has_entries(saturated=3))

    # fmt: off
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'tenant_uuid': OTHER_TENANT})
    @stat_call_on_queue({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'tenant_uuid': USERS_TENANT})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'answered': 1, 'tenant_uuid': OTHER_TENANT})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'answered': 2, 'tenant_uuid': USERS_TENANT})
    # fmt: on
    def test_get_interval_filtered_by_tenant(self):
        tenant_uuids = [USERS_TENANT]
        result = self.dao.queue_stat.get_interval(tenant_uuids, qos_threshold=0)
        res = 2
        assert_that(result[0], has_entries(queue_id=2, answered=res, qos=self.qos(res, 1)))

    # fmt: off
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'tenant_uuid': OTHER_TENANT})
    @stat_call_on_queue({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'tenant_uuid': USERS_TENANT})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'answered': 1, 'tenant_uuid': OTHER_TENANT})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'answered': 2, 'tenant_uuid': USERS_TENANT})
    # fmt: on
    def test_get_interval_filtered_by_empty_tenant(self):
        tenant_uuids = []
        result = self.dao.queue_stat.get_interval(tenant_uuids, qos_threshold=0)
        assert_that(result, empty())

    @stat_call_on_queue(
        {
            'queue_id': 1,
            'time': '2020-10-01 13:00:00',
            'waittime': 0,
            'status': 'answered',
        }
    )
    @stat_call_on_queue(
        {
            'queue_id': 1,
            'time': '2020-10-01 14:00:00',
            'waittime': 10,
            'status': 'abandoned',
        }
    )
    @stat_queue_periodic(
        {
            'queue_id': 1,
            'time': '2020-10-01 13:00:00',
            'answered': 1,
            'abandoned': 1,
            'total': 1,
            'full': 1,
            'closed': 1,
            'joinempty': 1,
            'leaveempty': 1,
            'divert_ca_ratio': 1,
            'divert_waittime': 1,
            'timeout': 1,
        }
    )
    @stat_queue_periodic(
        {
            'queue_id': 1,
            'time': '2020-10-01 14:00:00',
            'answered': 1,
            'abandoned': 1,
            'total': 1,
            'full': 1,
            'closed': 1,
            'joinempty': 1,
            'leaveempty': 1,
            'divert_ca_ratio': 1,
            'divert_waittime': 1,
            'timeout': 1,
        }
    )
    def test_get_interval_all_fields(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval(tenant_uuids, qos_threshold=0)
        assert_that(
            result[0],
            has_entries(
                queue_id=1,
                queue_name='queue',
                **{'from': '2020-10-01T13:00:00+00:00'},
                until='2020-10-01T14:00:00+00:00',
                answered=2,
                abandoned=2,
                total=2,
                full=2,
                closed=2,
                joinempty=2,
                leaveempty=2,
                divert_ca_ratio=2,
                divert_waittime=2,
                timeout=2,
                qos=50.0,
                answered_rate=14.29,
                average_waiting_time=1.25,
                blocking=4,
                saturated=6,
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 13:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 14:00:00', 'answered': 2})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 15:00:00', 'answered': 3})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-01 14:00:00', 'answered': 4})
    # fmt: on
    def test_get_interval_by_queue(self):
        tenant_uuids = None
        interval = {
            'from_': '2020-10-01 14:00:00',
            'until': '2020-10-01 16:00:00',
        }

        result = self.dao.queue_stat.get_interval_by_queue(tenant_uuids, 1, **interval)
        assert_that(result, has_entries(queue_id=1, answered=2 + 3))

    def test_get_interval_by_queue_without_result(self):
        tenant_uuids = None
        result = self.dao.queue_stat.get_interval_by_queue(tenant_uuids, 1)
        assert_that(result, equal_to(None))

    def qos(self, answered, nb_calls):
        return round(100.0 * nb_calls / answered, 2)
