# Copyright 2020-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from hamcrest import assert_that, calling, contains_exactly, raises

from wazo_call_logd.plugins.support_center.exceptions import RangeTooLargeException
from wazo_call_logd.plugins.support_center.services import QueueStatisticsService

MTL_TZ = ZoneInfo('America/Montreal')


class TestSupportCenterService(TestCase):
    def setUp(self):
        self.service = QueueStatisticsService(None)

    def test_that_intervals_stays_within_limits(self):
        from_ = datetime.fromisoformat('2020-10-10T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-10-12T12:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('day', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-10-10T00:00:00-04:00',
                    '2020-10-11T00:00:00-04:00',
                ),
                (
                    '2020-10-11T00:00:00-04:00',
                    '2020-10-12T00:00:00-04:00',
                ),
                (
                    '2020-10-12T00:00:00-04:00',
                    '2020-10-12T12:00:00-04:00',
                ),
            ),
        )

    def test_when_interval_is_hour_and_range_is_too_large(self):
        from_ = datetime.fromisoformat('2020-10-10T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-11-15T00:00:00').replace(tzinfo=MTL_TZ)
        assert_that(
            calling(list).with_args(
                self.service._generate_interval('hour', from_, until, MTL_TZ)
            ),
            raises(RangeTooLargeException),
        )

    def test_that_hourly_interval_changes_dst_up(self):
        from_ = datetime.fromisoformat('2020-10-31T23:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-11-01T02:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('hour', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-10-31T23:00:00-04:00',
                    '2020-11-01T00:00:00-04:00',
                ),
                (
                    '2020-11-01T00:00:00-04:00',
                    '2020-11-01T01:00:00-04:00',
                ),
                (
                    '2020-11-01T01:00:00-04:00',
                    '2020-11-01T01:00:00-05:00',
                ),
                (
                    '2020-11-01T01:00:00-05:00',
                    '2020-11-01T02:00:00-05:00',
                ),
            ),
        )

    def test_that_daily_interval_changes_dst_up(self):
        from_ = datetime.fromisoformat('2020-10-31T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-11-02T00:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('day', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-10-31T00:00:00-04:00',
                    '2020-11-01T00:00:00-04:00',
                ),
                (
                    '2020-11-01T00:00:00-04:00',
                    '2020-11-02T00:00:00-05:00',
                ),
            ),
        )

    def test_that_monthly_interval_changes_dst_up(self):
        from_ = datetime.fromisoformat('2020-10-01T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-12-01T00:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('month', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-10-01T00:00:00-04:00',
                    '2020-11-01T00:00:00-04:00',
                ),
                (
                    '2020-11-01T00:00:00-04:00',
                    '2020-12-01T00:00:00-05:00',
                ),
            ),
        )

    def test_that_hourly_interval_changes_dst_down(self):
        from_ = datetime.fromisoformat('2020-03-07T23:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-03-08T04:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('hour', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-03-07T23:00:00-05:00',
                    '2020-03-08T00:00:00-05:00',
                ),
                (
                    '2020-03-08T00:00:00-05:00',
                    '2020-03-08T01:00:00-05:00',
                ),
                (
                    '2020-03-08T01:00:00-05:00',
                    '2020-03-08T03:00:00-04:00',
                ),
                (
                    '2020-03-08T03:00:00-04:00',
                    '2020-03-08T04:00:00-04:00',
                ),
            ),
        )

    def test_that_daily_interval_changes_dst_down(self):
        from_ = datetime.fromisoformat('2020-03-07T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-03-09T00:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('day', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-03-07T00:00:00-05:00',
                    '2020-03-08T00:00:00-05:00',
                ),
                (
                    '2020-03-08T00:00:00-05:00',
                    '2020-03-09T00:00:00-04:00',
                ),
            ),
        )

    def test_that_monthly_interval_changes_dst_down(self):
        from_ = datetime.fromisoformat('2020-03-01T00:00:00').replace(tzinfo=MTL_TZ)
        until = datetime.fromisoformat('2020-05-01T00:00:00').replace(tzinfo=MTL_TZ)
        intervals = list(self.service._generate_interval('month', from_, until, MTL_TZ))
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains_exactly(
                (
                    '2020-03-01T00:00:00-05:00',
                    '2020-04-01T00:00:00-04:00',
                ),
                (
                    '2020-04-01T00:00:00-04:00',
                    '2020-05-01T00:00:00-04:00',
                ),
            ),
        )

    def test_qos_interval_empty(self):
        intervals = list(self.service._generate_qos_interval([]))
        assert_that(
            intervals,
            contains_exactly(
                (0, None),
            ),
        )

    def test_qos_interval_one(self):
        intervals = list(self.service._generate_qos_interval([1]))
        assert_that(
            intervals,
            contains_exactly(
                (0, 1),
                (1, None),
            ),
        )

    def test_qos_interval_multiple(self):
        intervals = list(self.service._generate_qos_interval([1, 2, 3, 4]))
        assert_that(
            intervals,
            contains_exactly(
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 4),
                (4, None),
            ),
        )
