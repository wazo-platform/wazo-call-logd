# -*- coding: utf-8 -*-
# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    empty,
    equal_to,
    has_entries,
    has_entry,
    has_items,
    has_properties,
    not_,
)
from xivo_test_helpers import until
from xivo_test_helpers.hamcrest.raises import raises

from wazo_call_logd_client.exceptions import CallLogdError

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TENANT
from .helpers.database import stat_queue_periodic, stat_call_on_queue
from .helpers.hamcrest.contains_string_ignoring_case import (
    contains_string_ignoring_case,
)


class BaseTest(IntegrationTest):

    def _assert_error(self, expected_error_code, command, **kwargs):
        assert_that(
            calling(command).with_args(**kwargs),
            raises(CallLogdError).matching(has_properties(status_code=expected_error_code)),
        )


class TestNoAuth(BaseTest):

    asset = 'base'

    def test_given_no_auth_when_list_queues_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.queue_statistics.list),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_list_queues_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.queue_statistics.list),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )

    def test_given_no_auth_when_get_queue_stats_by_id_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.queue_statistics.get_by_id).with_args(queue_id=33),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_get_queue_stats_by_id_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.queue_statistics.get_by_id).with_args(queue_id=33),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )


class TestInputParameters(BaseTest):

    asset = 'base'

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'answered': 1})
    # fmt: on
    def test_that_getting_queue_stats_with_wrong_parameters_raises_error(self):
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, from_='test'
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, from_=False
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, from_=1234
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            from_='2020-10-05',
        )

        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, until='test'
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, until=False
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, until=1234
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            until='2020-10-05',
        )

        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            qos_threshold='test',
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            qos_threshold=False,
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            qos_threshold=124.2,
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            qos_threshold='2020-10-06 10:00:00',
        )

        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, interval='test'
        )

        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            start_time='test',
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, start_time=False
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, start_time=124
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, start_time=124.5
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            start_time='2020-10-06 10:00:00',
        )

        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, end_time='test'
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, end_time=False
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, end_time=124
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.get_by_id, queue_id=1, end_time=124.5
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            end_time='2020-10-06 10:00:00',
        )

        self._assert_error(
            400,
            self.call_logd.queue_statistics.get_by_id,
            queue_id=1,
            from_='2020-10-01 00:00:00',
            until='2020-11-01 00:00:01',
            interval='hour',
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'answered': 1})
    # fmt: on
    def test_that_listing_queues_with_wrong_parameters_raises_errors(self):
        self._assert_error(400, self.call_logd.queue_statistics.list, from_='test')
        self._assert_error(400, self.call_logd.queue_statistics.list, from_=False)
        self._assert_error(400, self.call_logd.queue_statistics.list, from_=1234)

        self._assert_error(400, self.call_logd.queue_statistics.list, until='test')
        self._assert_error(400, self.call_logd.queue_statistics.list, until=False)
        self._assert_error(400, self.call_logd.queue_statistics.list, until=1234)

        self._assert_error(
            400, self.call_logd.queue_statistics.list, qos_threshold='test'
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.list, qos_threshold=False
        )
        self._assert_error(
            400, self.call_logd.queue_statistics.list, qos_threshold=124.2
        )
        self._assert_error(
            400,
            self.call_logd.queue_statistics.list,
            qos_threshold='2020-10-06 10:00:00',
        )

        self._assert_error(400, self.call_logd.queue_statistics.list, interval='day')


class TestStatistics(BaseTest):

    asset = 'base'

    def test_list_queue_statistics_when_no_stats(self):
        results = self.call_logd.queue_statistics.list()
        assert_that(
            results,
            has_entries(
                items=empty(),
                total=equal_to(0),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 1, 'answered': 1})
    # fmt: on
    def test_list_queue_statistics_period_no_interval(self):
        results = self.call_logd.queue_statistics.list(from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00')
        assert_that(
            results,
            has_entries(
                {
                    'items': has_items(
                        has_entries({
                            'from': '2020-10-01T00:00:00+00:00',
                            'until': '2020-11-01T00:00:00+00:00',
                            'tenant_uuid': MASTER_TENANT,
                            'queue_id': 1,
                            'queue_name': 'queue',
                            'received': 1,
                            'answered': 1,
                            'abandoned': 0,
                            'closed': 0,
                            'not_answered': 0,
                            'saturated': 0,
                            'blocked': 0,
                            'average_waiting_time': 0,
                            'answered_rate': 100.0,
                            'quality_of_service': None,
                        })
                    ),
                    'total': equal_to(1),
                }
            )
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 4:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-06 7:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 3, 'time': '2020-10-06 13:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 4, 'time': '2020-11-01 00:00:00', 'answered': 1})
    # fmt: on
    def test_list_queue_statistics_multiple_queues_same_datetime(self):
        results = self.call_logd.queue_statistics.list(from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00+00:00')
        assert_that(
            results,
            has_entries(
                {
                    'items': has_items(
                        has_entries({
                            'from': '2020-10-01T00:00:00+00:00',
                            'until': '2020-11-01T00:00:00+00:00',
                            'queue_id': 1,
                            'queue_name': 'queue',
                        }),
                        has_entries({
                            'from': '2020-10-01T00:00:00+00:00',
                            'until': '2020-11-01T00:00:00+00:00',
                            'queue_id': 2,
                            'queue_name': 'queue',
                            'answered': 1,
                        }),
                        has_entries({
                            'from': '2020-10-01T00:00:00+00:00',
                            'until': '2020-11-01T00:00:00+00:00',
                            'queue_id': 3,
                            'queue_name': 'queue',
                            'answered': 1,
                        }),
                    ),
                    'total': equal_to(3),
                }
            )
        )

    def test_get_queue_no_interval_returns_from_to_until(self):
        pass