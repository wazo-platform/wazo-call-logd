# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from hamcrest import (
    assert_that,
    contains,
)
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from wazo_call_logd.plugins.support_center.service import QueueStatisticsService


class TestSupportCenterService(TestCase):

    def setUp(self):
        self.service = QueueStatisticsService(None)

    def test_that_intervals_stays_within_limits(self):
        from_ = datetime.fromisoformat('2020-10-10T00:00:00')
        until = datetime.fromisoformat('2020-10-12T12:00:00')
        result = list(self.service._generate_subinterval(from_, until, relativedelta(days=1)))
        assert_that(result, contains(
            (datetime.fromisoformat('2020-10-10T00:00:00'), datetime.fromisoformat('2020-10-11T00:00:00')),
            (datetime.fromisoformat('2020-10-11T00:00:00'), datetime.fromisoformat('2020-10-12T00:00:00')),
            (datetime.fromisoformat('2020-10-12T00:00:00'), datetime.fromisoformat('2020-10-12T12:00:00')),
        ))
