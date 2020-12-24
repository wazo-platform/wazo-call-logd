# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytz

from datetime import datetime
from hamcrest import (
    assert_that,
    contains,
)
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from wazo_call_logd.plugins.support_center.services import QueueStatisticsService

MTL_TZ = pytz.timezone('America/Montreal')


class TestSupportCenterService(TestCase):
    def setUp(self):
        self.service = QueueStatisticsService(None)

    def test_that_intervals_stays_within_limits(self):
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-10-10T00:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-10-12T12:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(days=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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

    def test_that_hourly_interval_changes_dst_up(self):
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-10-31T23:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-11-01T02:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(hours=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
                (
                    '2020-10-31T23:00:00-04:00',
                    '2020-11-01T00:00:00-04:00',
                ),
                (
                    '2020-11-01T00:00:00-04:00',
                    '2020-11-01T01:00:00-05:00',
                ),
                (
                    '2020-11-01T01:00:00-05:00',
                    '2020-11-01T02:00:00-05:00',
                ),
            ),
        )

    def test_that_daily_interval_changes_dst_up(self):
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-10-31T00:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-11-02T00:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(days=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-10-01T00:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-12-01T00:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(months=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-03-07T23:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-03-08T04:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(hours=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-03-07T00:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-03-09T00:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(days=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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
        from_ = MTL_TZ.localize(datetime.fromisoformat('2020-03-01T00:00:00'))
        until = MTL_TZ.localize(datetime.fromisoformat('2020-05-01T00:00:00'))
        intervals = list(
            self.service._generate_subinterval(
                from_, until, relativedelta(months=1), MTL_TZ
            )
        )
        result = [(d1.isoformat(), d2.isoformat()) for d1, d2 in intervals]
        assert_that(
            result,
            contains(
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
            contains(
                (0, None),
            ),
        )

    def test_qos_interval_one(self):
        intervals = list(self.service._generate_qos_interval([1]))
        assert_that(
            intervals,
            contains(
                (0, 1),
                (1, None),
            ),
        )

    def test_qos_interval_multiple(self):
        intervals = list(self.service._generate_qos_interval([1, 2, 3, 4]))
        assert_that(
            intervals,
            contains(
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 4),
                (4, None),
            ),
        )
