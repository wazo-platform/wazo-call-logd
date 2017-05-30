# -*- coding: utf-8 -*-

# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
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

from unittest import TestCase

from hamcrest import all_of, assert_that, equal_to, has_property
from mock import Mock, patch

from xivo_call_logs.raw_call_log import RawCallLog
from xivo_call_logs.exceptions import InvalidCallLogException


@patch('xivo_call_logs.raw_call_log.CallLog', Mock)
class TestRawCallLog(TestCase):
    def setUp(self):
        self.raw_call_log = RawCallLog()

    def test_to_call_log(self):
        self.raw_call_log.date = Mock()
        self.raw_call_log.date_answer = Mock()
        self.raw_call_log.date_end = Mock()
        self.raw_call_log.source_name = Mock()
        self.raw_call_log.source_exten = Mock()
        self.raw_call_log.destination_name = Mock()
        self.raw_call_log.destination_exten = Mock()
        self.raw_call_log.user_field = Mock()
        self.raw_call_log.cel_ids = [1, 2, 3]

        result = self.raw_call_log.to_call_log()

        assert_that(result, all_of(
            has_property('date', self.raw_call_log.date),
            has_property('date_answer', self.raw_call_log.date_answer),
            has_property('date_end', self.raw_call_log.date_end),
            has_property('source_name', self.raw_call_log.source_name),
            has_property('source_exten', self.raw_call_log.source_exten),
            has_property('destination_name', self.raw_call_log.destination_name),
            has_property('destination_exten', self.raw_call_log.destination_exten),
            has_property('user_field', self.raw_call_log.user_field),
        ))
        assert_that(result.cel_ids, equal_to([1, 2, 3]))

    def test_to_call_log_invalid_date(self):
        self.raw_call_log.date = None

        self.assertRaises(InvalidCallLogException, self.raw_call_log.to_call_log)

    def test_to_call_log_with_no_source(self):
        self.raw_call_log.source_name = u''
        self.raw_call_log.source_exten = u''

        self.assertRaises(InvalidCallLogException, self.raw_call_log.to_call_log)
