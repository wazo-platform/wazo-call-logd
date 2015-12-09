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

from unittest import TestCase

from hamcrest import all_of, assert_that, contains, contains_inanyorder, equal_to, has_property
from mock import Mock

from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.exceptions import InvalidCallLogException


class TestCallLogsGenerator(TestCase):
    def setUp(self):
        self.cel_dispatcher = Mock(CELDispatcher)
        self.generator = CallLogsGenerator(self.cel_dispatcher)

    def tearDown(self):
        pass

    def test_from_cel(self):
        self.generator.call_logs_from_cel = Mock()
        self.generator.list_call_log_ids = Mock()
        expected_calls = self.generator.call_logs_from_cel.return_value = Mock()
        expected_to_delete = self.generator.list_call_log_ids.return_value = Mock()
        cels = Mock()

        result = self.generator.from_cel(cels)

        self.generator.call_logs_from_cel.assert_called_once_with(cels)
        assert_that(result, all_of(has_property('new_call_logs', expected_calls),
                                   has_property('call_logs_to_delete', expected_to_delete)))

    def test_call_logs_from_cel_no_cels(self):
        cels = []

        result = self.generator.call_logs_from_cel(cels)

        assert_that(result, equal_to([]))

    def test_call_logs_from_cel_one_call(self):
        linkedid = '9328742934'
        cels = self._generate_cel_for_call([linkedid])
        call = self.cel_dispatcher.interpret_call.return_value = Mock()

        result = self.generator.call_logs_from_cel(cels)

        self.cel_dispatcher.interpret_call.assert_called_once_with(cels)
        assert_that(result, contains(call))

    def test_call_logs_from_cel_two_calls(self):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1, call_2 = self.cel_dispatcher.interpret_call.side_effect = [Mock(), Mock()]

        result = self.generator.call_logs_from_cel(cels)

        self.cel_dispatcher.interpret_call.assert_any_call(cels_1)
        self.cel_dispatcher.interpret_call.assert_any_call(cels_2)
        assert_that(result, contains(call_1, call_2))

    def test_call_logs_from_cel_two_calls_one_valid_one_invalid(self):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1, _ = self.cel_dispatcher.interpret_call.side_effect = [Mock(), InvalidCallLogException()]

        result = self.generator.call_logs_from_cel(cels)

        self.cel_dispatcher.interpret_call.assert_any_call(cels_1)
        self.cel_dispatcher.interpret_call.assert_any_call(cels_2)
        assert_that(result, contains(call_1))

    def test_list_call_log_ids(self):
        cel_1, cel_2 = Mock(call_log_id=1), Mock(call_log_id=1)
        cel_3, cel_4 = Mock(call_log_id=2), Mock(call_log_id=None)
        cels = [cel_1, cel_2, cel_3, cel_4]

        result = self.generator.list_call_log_ids(cels)

        assert_that(result, contains_inanyorder(1, 2))

    def _generate_cel_for_call(self, linked_id, cel_count=3):
        result = []
        for _ in range(cel_count):
            result.append(Mock(linkedid=linked_id))

        return result
