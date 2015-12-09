# -*- coding: utf-8 -*-

# Copyright (C) 2013-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import datetime
from unittest import TestCase

from hamcrest import all_of, assert_that, contains, equal_to, has_property
from mock import Mock, PropertyMock

from xivo_call_logs.raw_call_log import RawCallLog
from xivo_call_logs.exceptions import InvalidCallLogException


class TestRawCallLog(TestCase):
    def setUp(self):
        self.raw_call_log = RawCallLog()

    def tearDown(self):
        pass

    def test_to_call_log(self):
        self.raw_call_log.date = Mock()
        self.raw_call_log.source_name = Mock()
        self.raw_call_log.source_exten = Mock()
        self.raw_call_log.destination_name = Mock()
        self.raw_call_log.destination_exten = Mock()
        self.raw_call_log.user_field = Mock()
        self.raw_call_log.answered = Mock()
        self.raw_call_log.cel_ids = [1, 2, 3]
        type(self.raw_call_log).duration = PropertyMock()

        result = self.raw_call_log.to_call_log()

        assert_that(result, all_of(
            has_property('date', self.raw_call_log.date),
            has_property('source_name', self.raw_call_log.source_name),
            has_property('source_exten', self.raw_call_log.source_exten),
            has_property('destination_name', self.raw_call_log.destination_name),
            has_property('destination_exten', self.raw_call_log.destination_exten),
            has_property('user_field', self.raw_call_log.user_field),
            has_property('answered', self.raw_call_log.answered),
            has_property('duration', self.raw_call_log.duration)
        ))
        assert_that(result.get_related_cels(), contains(1, 2, 3))

    def test_to_call_log_invalid_date(self):
        self.raw_call_log.date = None

        self.assertRaises(InvalidCallLogException, self.raw_call_log.to_call_log)

    def test_duration_no_start_no_end(self):
        result = self.raw_call_log.duration

        assert_that(result, equal_to(datetime.timedelta(0)))

    def test_duration_with_start_but_no_end(self):
        self.raw_call_log.communication_start = datetime.datetime(year=2013, month=1, day=2)

        result = self.raw_call_log.duration

        assert_that(result, equal_to(datetime.timedelta(0)))

    def test_duration_with_end_but_no_start(self):
        self.raw_call_log.communication_start = datetime.datetime(year=2013, month=1, day=1)

        result = self.raw_call_log.duration

        assert_that(result, equal_to(datetime.timedelta(0)))

    def test_duration_with_start_and_end_none(self):
        self.raw_call_log.communication_start = None
        self.raw_call_log.communication_end = None

        result = self.raw_call_log.duration

        assert_that(result, equal_to(datetime.timedelta(0)))

    def test_duration_with_start_and_end(self):
        start = self.raw_call_log.communication_start = datetime.datetime(year=2013, month=1, day=1)
        end = self.raw_call_log.communication_end = datetime.datetime(year=2013, month=1, day=2)

        result = self.raw_call_log.duration

        assert_that(result, equal_to(end - start))

    def test_duration_negative(self):
        self.raw_call_log.communication_start = datetime.datetime(year=2013, month=1, day=2)
        self.raw_call_log.communication_end = datetime.datetime(year=2013, month=1, day=1)

        result = self.raw_call_log.duration

        assert_that(result, equal_to(datetime.timedelta(0)))
