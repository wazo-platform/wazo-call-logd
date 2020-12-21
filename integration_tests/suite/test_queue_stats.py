# -*- coding: utf-8 -*-
# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytz

from datetime import datetime
from dateutil.relativedelta import relativedelta
from hamcrest import (
    assert_that,
    calling,
    empty,
    equal_to,
    has_entries,
    has_items,
    has_properties,
)
from xivo_test_helpers.hamcrest.raises import raises

from wazo_call_logd_client.exceptions import CallLogdError

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TENANT
from .helpers.database import stat_queue, stat_queue_periodic, stat_call_on_queue
from .helpers.hamcrest.contains_string_ignoring_case import (
    contains_string_ignoring_case,
)


class TestNoAuth(IntegrationTest):

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
                calling(self.call_logd.queue_statistics.get_by_id).with_args(
                    queue_id=33
                ),
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


class TestInputParameters(IntegrationTest):

    asset = 'base'

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'answered': 1})
    # fmt: on
    def test_that_getting_queue_stats_with_wrong_parameters_raises_error(self):
        erronous_bodies = [
            # from_
            {'from_': 'test'},
            {'from_': False},
            {'from_': 1234},
            {'from_': '2020-10-05'},
            # until
            {'until': 'test'},
            {'until': False},
            {'until': 1234},
            {'until': '2020-10-05'},
            # qos_threshold
            {'qos_threshold': 'test'},
            {'qos_threshold': False},
            {'qos_threshold': 124.2},
            {'qos_threshold': '2020-10-06 10:00:00'},
            {'qos_threshold': -1},
            # interval
            {'interval': 'test'},
            # day_start_time
            {'day_start_time': 'test'},
            {'day_start_time': False},
            {'day_start_time': 124},
            {'day_start_time': 124.5},
            {'day_start_time': '2020-10-06 10:00:00'},
            {'day_start_time': '25:00'},
            {'day_start_time': '23:60'},
            # day_end_time
            {'day_end_time': 'test'},
            {'day_end_time': False},
            {'day_end_time': 124},
            {'day_end_time': 124.5},
            {'day_end_time': '2020-10-06 10:00:00'},
            {'day_end_time': '25:00'},
            {'day_end_time': '23:60'},
            # Logic
            {'day_end_time': '22:00', 'day_start_time': '23:00'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-09T23:59:59'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-10T00:00:00+01:00'},
            # Too long
            {
                'from_': '2020-10-01 00:00:00',
                'until': '2020-11-01 00:00:01',
                'interval': 'hour',
            },
            # week_days
            {'week_days': 42},
            {'week_days': '6,7,8'},
            {'week_days': 'test'},
            {'week_days': False},
            # Timezone
            {'timezone': 'invalid'},
            {'timezone': 1234},
        ]

        for body in erronous_bodies:
            assert_that(
                calling(self.call_logd.queue_statistics.get_by_id).with_args(
                    queue_id=1, **body
                ),
                raises(CallLogdError).matching(has_properties(status_code=400)),
                body,
            )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'answered': 1})
    # fmt: on
    def test_that_getting_queue_qos_stats_with_wrong_parameters_raises_error(self):
        erronous_bodies = [
            # from_
            {'from_': 'test'},
            {'from_': False},
            {'from_': 1234},
            {'from_': '2020-10-05'},
            # until
            {'until': 'test'},
            {'until': False},
            {'until': 1234},
            {'until': '2020-10-05'},
            # qos_thresholds
            {'qos_thresholds': 'test'},
            {'qos_thresholds': False},
            {'qos_thresholds': 124.2},
            {'qos_thresholds': '2020-10-06 10:00:00'},
            {'qos_thresholds': -1},
            {'qos_thresholds': '-1'},
            {'qos_thresholds': '3,-1'},
            # interval
            {'interval': 'test'},
            # day_start_time
            {'day_start_time': 'test'},
            {'day_start_time': False},
            {'day_start_time': 124},
            {'day_start_time': 124.5},
            {'day_start_time': '2020-10-06 10:00:00'},
            {'day_start_time': '25:00'},
            {'day_start_time': '23:60'},
            # day_end_time
            {'day_end_time': 'test'},
            {'day_end_time': False},
            {'day_end_time': 124},
            {'day_end_time': 124.5},
            {'day_end_time': '2020-10-06 10:00:00'},
            {'day_end_time': '25:00'},
            {'day_end_time': '23:60'},
            # Logic
            {'day_end_time': '22:00', 'day_start_time': '23:00'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-09T23:59:59'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-10T00:00:00+01:00'},
            # Too long
            {
                'from_': '2020-10-01 00:00:00',
                'until': '2020-11-01 00:00:01',
                'interval': 'hour',
            },
            # week_days
            {'week_days': 42},
            {'week_days': '6,7,8'},
            {'week_days': 'test'},
            {'week_days': False},
            # Timezone
            {'timezone': 'invalid'},
            {'timezone': 1234},
        ]

        for body in erronous_bodies:
            assert_that(
                calling(self.call_logd.queue_statistics.get_qos_by_id).with_args(
                    queue_id=1, **body
                ),
                raises(CallLogdError).matching(has_properties(status_code=400)),
                body,
            )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'answered': 1})
    # fmt: on
    def test_that_listing_queues_with_wrong_parameters_raises_errors(self):
        erronous_bodies = [
            # from_
            {'from_': 'test'},
            {'from_': False},
            {'from_': 1234},
            {'from_': '2020-10-05'},
            # until
            {'until': 'test'},
            {'until': False},
            {'until': 1234},
            {'until': '2020-10-05'},
            # qos_threshold
            {'qos_threshold': 'test'},
            {'qos_threshold': False},
            {'qos_threshold': 124.2},
            {'qos_threshold': '2020-10-06 10:00:00'},
            {'qos_threshold': -1},
            # day_start_time
            {'day_start_time': 'test'},
            {'day_start_time': False},
            {'day_start_time': 124},
            {'day_start_time': 124.5},
            {'day_start_time': '2020-10-06 10:00:00'},
            {'day_start_time': '25:00'},
            {'day_start_time': '23:60'},
            # day_end_time
            {'day_end_time': 'test'},
            {'day_end_time': False},
            {'day_end_time': 124},
            {'day_end_time': 124.5},
            {'day_end_time': '2020-10-06 10:00:00'},
            {'day_end_time': '25:00'},
            {'day_end_time': '23:60'},
            # Logic
            {'day_end_time': '22:00', 'day_start_time': '23:00'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-09T23:59:59'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-10T00:00:00+01:00'},
            # week_days
            {'week_days': 42},
            {'week_days': '6,7,8'},
            {'week_days': 'test'},
            {'week_days': False},
            # Timezone
            {'timezone': 'invalid'},
            {'timezone': 1234},
        ]

        for body in erronous_bodies:
            assert_that(
                calling(self.call_logd.queue_statistics.list).with_args(**body),
                raises(CallLogdError).matching(has_properties(status_code=400)),
                body,
            )


class TestStatistics(IntegrationTest):

    asset = 'base'

    def _get_tomorrow(self, timezone=None):
        timezone = timezone or pytz.utc
        today = timezone.normalize(timezone.localize(datetime.now()))
        return timezone.normalize(
            timezone.localize(
                datetime(today.year, today.month, today.day) + relativedelta(days=1)
            )
        ).isoformat(timespec='seconds')

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
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-05 13:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-06 13:00:00', 'total': 2, 'answered': 2})
    # fmt: on
    def test_list_queue_statistics_when_no_param_with_stats(self):
        results = self.call_logd.queue_statistics.list()
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-05T13:00:00+00:00'},
                        until=self._get_tomorrow(),
                        tenant_uuid=MASTER_TENANT,
                        queue_id=1,
                        queue_name='queue',
                        received=1,
                        answered=1,
                        abandoned=0,
                        closed=0,
                        not_answered=0,
                        saturated=0,
                        blocked=0,
                        average_waiting_time=0,
                        answered_rate=100.0,
                        quality_of_service=None,
                    ),
                    has_entries(
                        **{'from': '2020-10-06T13:00:00+00:00'},
                        until=self._get_tomorrow(),
                        tenant_uuid=MASTER_TENANT,
                        queue_id=2,
                        queue_name='queue',
                        received=2,
                        answered=2,
                        abandoned=0,
                        closed=0,
                        not_answered=0,
                        saturated=0,
                        blocked=0,
                        average_waiting_time=0,
                        answered_rate=100.0,
                        quality_of_service=None,
                    ),
                ),
                total=equal_to(2),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-05T13:00:00+00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-06T13:00:00+00:00', 'total': 2, 'answered': 2})
    # fmt: on
    def test_list_queue_statistics_when_no_param_except_timezone_with_stats(self):
        results = self.call_logd.queue_statistics.list(timezone='America/Montreal')
        timezone = pytz.timezone('America/Montreal')
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-05T09:00:00-04:00'},
                        until=self._get_tomorrow(timezone),
                        tenant_uuid=MASTER_TENANT,
                        queue_id=1,
                        queue_name='queue',
                        received=1,
                        answered=1,
                        abandoned=0,
                        closed=0,
                        not_answered=0,
                        saturated=0,
                        blocked=0,
                        average_waiting_time=0,
                        answered_rate=100.0,
                        quality_of_service=None,
                    ),
                    has_entries(
                        **{'from': '2020-10-06T09:00:00-04:00'},
                        until=self._get_tomorrow(timezone),
                        tenant_uuid=MASTER_TENANT,
                        queue_id=2,
                        queue_name='queue',
                        received=2,
                        answered=2,
                        abandoned=0,
                        closed=0,
                        not_answered=0,
                        saturated=0,
                        blocked=0,
                        average_waiting_time=0,
                        answered_rate=100.0,
                        quality_of_service=None,
                    ),
                ),
                total=equal_to(2),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 1, 'answered': 1})
    # fmt: on
    def test_list_queue_statistics_period_no_interval(self):
        results = self.call_logd.queue_statistics.list(
            from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00'
        )
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        tenant_uuid=MASTER_TENANT,
                        queue_id=1,
                        queue_name='queue',
                        received=1,
                        answered=1,
                        abandoned=0,
                        closed=0,
                        not_answered=0,
                        saturated=0,
                        blocked=0,
                        average_waiting_time=0,
                        answered_rate=100.0,
                        quality_of_service=None,
                    )
                ),
                total=equal_to(1),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 4:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 2, 'time': '2020-10-06 7:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 3, 'time': '2020-10-06 13:00:00', 'answered': 1})
    @stat_queue_periodic({'queue_id': 4, 'time': '2020-11-01 00:00:00', 'answered': 1})
    @stat_queue({'queue_id': 5})
    # fmt: on
    def test_list_queue_statistics_multiple_queues_same_datetime(self):
        results = self.call_logd.queue_statistics.list(
            from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00+00:00'
        )
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        queue_id=1,
                        queue_name='queue',
                        answered=1,
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        queue_id=2,
                        queue_name='queue',
                        answered=1,
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        queue_id=3,
                        queue_name='queue',
                        answered=1,
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        queue_id=4,
                        queue_name='queue',
                        answered=0,
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        queue_id=5,
                        queue_name='queue',
                        answered=0,
                    ),
                ),
                total=equal_to(5),
            ),
        )

    def test_get_queue_non_existing(self):
        assert_that(
            calling(self.call_logd.queue_statistics.get_by_id).with_args(queue_id=1),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 7:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-10 16:00:00', 'total': 3, 'answered': 3})
    # fmt: on
    def test_get_queue_no_params(self):
        results = self.call_logd.queue_statistics.get_by_id(queue_id=1)
        assert_that(results, has_entries(total=equal_to(1)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T07:00:00+00:00'},
                    until=self._get_tomorrow(),
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=9,
                    answered=9,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                )
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 7:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-10 16:00:00', 'total': 3, 'answered': 3})
    # fmt: on
    def test_get_queue_no_interval_returns_from_to_until(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06T00:00:00+00:00',
            until='2020-10-07T00:00:00+00:00',
        )
        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=6,
                    answered=6,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                )
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 4:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 5:00:00', 'total': 36, 'closed': 1, 'abandoned': 2, 'joinempty': 3, 'leaveempty': 4, 'timeout': 5, 'divert_ca_ratio': 6, 'divert_waittime': 7, 'full': 8})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 23:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 00:00:00', 'total': 1, 'answered': 1})
    # fmt: on
    def test_get_queue_interval_by_hour(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='hour',
        )
        assert_that(results, has_entries(total=equal_to(25)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T04:00:00+00:00'},
                    until='2020-10-06T05:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=1,
                    answered=1,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T05:00:00+00:00'},
                    until='2020-10-06T06:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=36,
                    answered=0,
                    abandoned=2,
                    closed=1,
                    not_answered=5,
                    saturated=6 + 7 + 8,
                    blocked=3 + 4,
                    average_waiting_time=0,
                    answered_rate=0.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T13:00:00+00:00'},
                    until='2020-10-06T14:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=0,
                    answered=0,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=None,
                    answered_rate=None,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=38,
                    answered=2,
                    abandoned=2,
                    closed=1,
                    not_answered=5,
                    saturated=6 + 7 + 8,
                    blocked=3 + 4,
                    average_waiting_time=0,
                    answered_rate=8.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 3, 'answered': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'waittime': 20})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-06 13:12:00', 'waittime': 5})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-06 13:18:00', 'waittime': 3})
    # fmt: on
    def test_get_specific_queue_qos(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 13:00:00',
            until='2020-10-06 14:00:00',
            interval='hour',
            qos_threshold=10,
        )

        assert_that(results, has_entries(total=equal_to(2)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T13:00:00+00:00'},
                    until='2020-10-06T14:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    average_waiting_time=9,
                    quality_of_service=66.67,
                )
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 7:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 13:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 16:00:00', 'total': 3, 'answered': 3})
    # fmt: on
    def test_get_queue_when_call_out_of_time_range(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='hour',
            day_start_time='08:00',
            day_end_time='17:00',
        )

        assert_that(results, has_entries(total=equal_to(10)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T08:00:00+00:00'},
                    until='2020-10-06T09:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=0,
                    answered=0,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=None,
                    answered_rate=None,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T13:00:00+00:00'},
                    until='2020-10-06T14:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T16:00:00+00:00'},
                    until='2020-10-06T17:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 7:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 13:00:00', 'total': 2, 'answered': 2})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-08 18:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-09 18:00:00', 'total': 4, 'answered': 4})
    # fmt: on
    def test_get_queue_when_call_not_in_week_days(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 00:00:00',
            until='2020-10-10 00:00:00',
            interval='day',
            week_days='3,4',
        )

        assert_that(results, has_entries(total=equal_to(3)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2,
                    answered=2,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-08T00:00:00+00:00'},
                    until='2020-10-09T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-10T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=5,
                    answered=5,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-06 23:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 00:00:00', 'total': 2, 'answered': 2})
    # fmt: on
    def test_get_queue_stats_week_days_hours_overlapping(self):
        # 2020-10-06 is the 2nd week day
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 23:00:00',
            until='2020-10-07 01:00:00',
            interval='hour',
            week_days='2',
        )

        assert_that(results, has_entries(total=equal_to(2)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=1,
                    answered=1,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=1,
                    answered=1,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

        # 2020-10-07 is the 3rd week day
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 23:00:00',
            until='2020-10-07 01:00:00',
            interval='hour',
            week_days='3',
        )

        assert_that(results, has_entries(total=equal_to(2)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2,
                    answered=2,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2,
                    answered=2,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0.0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-05 23:00:00', 'total': 1, 'answered': 1})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 00:00:00', 'total': 2, 'answered': 2})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 15:00:00', 'total': 3, 'answered': 3})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-07 23:00:00', 'total': 4, 'answered': 4})
    # fmt: on
    def test_get_queue_stat_with_day_interval_and_time_period(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 00:00:00',
            until='2020-10-08 00:00:00',
            interval='day',
            day_start_time='08:00',
            day_end_time='17:00',
        )

        assert_that(results, has_entries(total=equal_to(3)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=0,
                    answered=0,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=None,
                    answered_rate=None,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    @stat_queue({'queue_id': 1, 'name': 'queue'})
    def test_that_get_queue_stats_by_day_when_no_stats(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='day',
        )

        assert_that(results, has_entries(total=equal_to(2)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    queue_id=1,
                    queue_name='queue',
                ),
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    queue_id=1,
                    queue_name='queue',
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-01 23:00:00', 'total': 1, 'answered': 1})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-12 10:00:00', 'total': 2, 'answered': 2})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-14 15:00:00', 'total': 3, 'answered': 3})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-14 20:00:00', 'total': 4, 'answered': 4})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-17 10:00:00', 'total': 5, 'answered': 5})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-18 10:00:00', 'total': 6, 'answered': 6})  # not counted
    # fmt: on
    def test_get_queue_stat_with_month_interval_and_time_period(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-01T00:00:00+00:00',
            until='2020-11-01T00:00:00+00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
        )

        assert_that(results, has_entries(total=equal_to(2)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-01T00:00:00+00:00'},
                    until='2020-11-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2 + 3,
                    answered=2 + 3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-10-01T00:00:00+00:00'},
                    until='2020-11-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2 + 3,
                    answered=2 + 3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-01-01T06:00:00+00:00', 'total': 1, 'answered': 1})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-02-12T10:00:00+00:00', 'total': 2, 'answered': 2})  # should be counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-03-31T15:00:00+00:00', 'total': 3, 'answered': 3})  # should be counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-03-31T18:00:00+00:00', 'total': 4, 'answered': 4})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_months_with_all_filters(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-01-01T00:00:00+00:00',
            until='2020-04-01T00:00:00+00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
        )

        assert_that(results, has_entries(total=equal_to(4)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-01-01T00:00:00+00:00'},
                    until='2020-02-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=0,
                    answered=0,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=None,
                    answered_rate=None,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-02-01T00:00:00+00:00'},
                    until='2020-03-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2,
                    answered=2,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-03-01T00:00:00+00:00'},
                    until='2020-04-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-01-01T00:00:00+00:00'},
                    until='2020-04-01T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2 + 3,
                    answered=2 + 3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-01-01T07:00:00-05:00', 'total': 1, 'answered': 1})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-02-12T8:00:00-05:00', 'total': 2, 'answered': 2})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-03-31T16:00:00-04:00', 'total': 3, 'answered': 3})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-03-31T18:00:00-04:00', 'total': 4, 'answered': 4})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_months_with_all_filters_and_timezone(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-01-01T00:00:00',
            until='2020-04-01T00:00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
            timezone='America/Montreal',
        )

        assert_that(results, has_entries(total=equal_to(4)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-01-01T00:00:00-05:00'},
                    until='2020-02-01T00:00:00-05:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=0,
                    answered=0,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=None,
                    answered_rate=None,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-02-01T00:00:00-05:00'},
                    until='2020-03-01T00:00:00-05:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2,
                    answered=2,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-03-01T00:00:00-05:00'},
                    until='2020-04-01T00:00:00-04:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=3,
                    answered=3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
                has_entries(
                    **{'from': '2020-01-01T00:00:00-05:00'},
                    until='2020-04-01T00:00:00-04:00',
                    tenant_uuid=MASTER_TENANT,
                    queue_id=1,
                    queue_name='queue',
                    received=2 + 3,
                    answered=2 + 3,
                    abandoned=0,
                    closed=0,
                    not_answered=0,
                    saturated=0,
                    blocked=0,
                    average_waiting_time=0,
                    answered_rate=100.0,
                    quality_of_service=None,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T17:00:00-04:00', 'total': 1, 'answered': 1})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T18:00:00-04:00', 'total': 2, 'answered': 2})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T08:00:00-05:00', 'total': 3, 'answered': 3})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T16:00:00-05:00', 'total': 4, 'answered': 4})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T7:00:00-05:00', 'total': 5, 'answered': 5})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T8:00:00-05:00', 'total': 6, 'answered': 6})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T16:00:00-05:00', 'total': 7, 'answered': 7})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T18:00:00-05:00', 'total': 8, 'answered': 8})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-03T16:00:00-05:00', 'total': 9, 'answered': 9})  # not counted
    # fmt: on
    def test_day_interval_multiple_days_with_all_filters_and_timezone(self):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-31T00:00:00-04:00',
            until='2020-11-03T00:00:00-05:00',
            interval='day',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3,4,5,7',
            timezone='America/Montreal',
        )

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
            'abandoned': 0,
            'closed': 0,
            'not_answered': 0,
            'saturated': 0,
            'blocked': 0,
            'average_waiting_time': 0,
            'answered_rate': 100.0,
            'quality_of_service': None,
        }
        assert_that(results, has_entries(total=equal_to(3)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-02T00:00:00-05:00',
                    received=7,
                    answered=7,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-02T00:00:00-05:00'},
                    until='2020-11-03T00:00:00-05:00',
                    received=13,
                    answered=13,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T00:00:00-04:00'},
                    until='2020-11-03T00:00:00-05:00',
                    received=20,
                    answered=20,
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T17:00:00-04:00', 'total': 1, 'answered': 1})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T18:00:00-04:00', 'total': 2, 'answered': 2})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T00:00:00-04:00', 'total': 3, 'answered': 3})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T01:00:00-04:00', 'total': 4, 'answered': 4})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T01:00:00-05:00', 'total': 5, 'answered': 5})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T02:00:00-05:00', 'total': 6, 'answered': 6})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T03:00:00-05:00', 'total': 7, 'answered': 7})  # counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T04:00:00-05:00', 'total': 8, 'answered': 8})  # not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T02:00:00-05:00', 'total': 9, 'answered': 9})  # not counted
    # fmt: on
    def test_hour_interval_multiple_hours_with_all_filters_and_timezone_dst_change(
        self,
    ):
        results = self.call_logd.queue_statistics.get_by_id(
            queue_id=1,
            from_='2020-10-31T00:00:00-04:00',  # DST change happens on 2020-11-01 02:00
            until='2020-11-02T03:00:00-05:00',
            interval='hour',
            day_start_time='00:00',
            day_end_time='03:00',
            week_days='2,3,4,5,7',
            timezone='America/Montreal',
        )

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
            'abandoned': 0,
            'closed': 0,
            'not_answered': 0,
            'saturated': 0,
            'blocked': 0,
            'average_waiting_time': 0,
            'answered_rate': 100.0,
            'quality_of_service': None,
        }

        assert_that(results, has_entries(total=equal_to(4)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-01T01:00:00-05:00',
                    received=7,
                    answered=7,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T01:00:00-05:00'},
                    until='2020-11-01T02:00:00-05:00',
                    received=5,
                    answered=5,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T02:00:00-05:00'},
                    until='2020-11-01T03:00:00-05:00',
                    received=6,
                    answered=6,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T00:00:00-04:00'},
                    until='2020-11-02T03:00:00-05:00',
                    received=25,
                    answered=25,
                ),
            ),
        )

    # fmt: off
    # Following is NOT in open hours/open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00-04:00', 'waittime': 15, 'status': 'abandoned'})
    # Following is in open hours/open days
    # 2020-10-31 11:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'total': 8, 'answered': 5, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # 2020-10-31 13:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T13:00:00-04:00', 'total': 6, 'answered': 3, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:18:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # fmt: on
    def test_qos_period_thresholds_by_hour_all_params(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(
            queue_id=1,
            from_='2020-10-30T00:00:00-04:00',
            until='2020-11-01T00:00:00-04:00',
            interval='hour',
            day_start_time='10:00',
            day_end_time='15:00',
            week_days='2,3,4,6',
            timezone='America/Montreal',
            qos_thresholds='5,10,15,20,30',
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(6)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T11:00:00-04:00'},
                    until='2020-10-31T12:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(
                            min=0,
                            max=5,
                            answered=1,
                            abandoned=1,
                        ),
                        has_entries(
                            min=5,
                            max=10,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=10,
                            max=15,
                            answered=1,
                            abandoned=1,
                        ),
                        has_entries(
                            min=15,
                            max=20,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=20,
                            max=30,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=30,
                            max=None,
                            answered=0,
                            abandoned=1,
                        ),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T13:00:00-04:00'},
                    until='2020-10-31T14:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(
                            min=0,
                            max=5,
                            answered=1,
                            abandoned=1,
                        ),
                        has_entries(
                            min=5,
                            max=10,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=10,
                            max=15,
                            answered=0,
                            abandoned=1,
                        ),
                        has_entries(
                            min=15,
                            max=20,
                            answered=0,
                            abandoned=0,
                        ),
                        has_entries(
                            min=20,
                            max=30,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=30,
                            max=None,
                            answered=0,
                            abandoned=1,
                        ),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-30T00:00:00-04:00'},
                    until='2020-11-01T00:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(
                            min=0,
                            max=5,
                            answered=2,
                            abandoned=2,
                        ),
                        has_entries(
                            min=5,
                            max=10,
                            answered=2,
                            abandoned=0,
                        ),
                        has_entries(
                            min=10,
                            max=15,
                            answered=1,
                            abandoned=2,
                        ),
                        has_entries(
                            min=15,
                            max=20,
                            answered=1,
                            abandoned=0,
                        ),
                        has_entries(
                            min=20,
                            max=30,
                            answered=2,
                            abandoned=0,
                        ),
                        has_entries(
                            min=30,
                            max=None,
                            answered=0,
                            abandoned=2,
                        ),
                    ),
                ),
            ),
        )

    # fmt: off
    # Following is NOT in open hours/open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00+00:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00+00:00', 'waittime': 10, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00+00:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00+00:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00+00:00', 'total': 1, 'abandoned': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00+00:00', 'waittime': 15, 'status': 'abandoned'})
    # fmt: on
    def test_qos_period_thresholds_no_param(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(queue_id=1)
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-30T11:00:00+00:00'},
                    until=self._get_tomorrow(),
                    quality_of_service=has_items(
                        has_entries(
                            min=0,
                            max=None,
                            answered=2,
                            abandoned=1,
                        ),
                    ),
                ),
            ),
        )
