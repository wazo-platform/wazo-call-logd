# -*- coding: utf-8 -*-

# Copyright (C) 2013 Avencall
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

from hamcrest import all_of, assert_that, has_property
from mock import Mock
from unittest import TestCase

from xivo_call_logs.raw_call_log import RawCallLog


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
        self.raw_call_log.duration = Mock()

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
