# -*- coding: utf-8 -*-

# Copyright (C) 2013-2017 The Wazo Authors  (see the AUTHORS file)
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

from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import calling
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_property
from hamcrest import is_
from hamcrest import raises
from mock import ANY
from mock import Mock
from mock import patch
from unittest import TestCase

from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.exceptions import InvalidCallLogException


class TestCallLogsGenerator(TestCase):
    def setUp(self):
        self.interpretor = Mock()
        self.generator = CallLogsGenerator([self.interpretor])

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

    @patch('xivo_call_logs.raw_call_log.RawCallLog')
    def test_call_logs_from_cel_one_call(self, raw_call_log_constructor):
        linkedid = '9328742934'
        cels = self._generate_cel_for_call([linkedid])
        call = raw_call_log_constructor.return_value = self.interpretor.interpret_cels.return_value
        expected_call = call.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_called_once_with(cels, call)
        assert_that(result, contains(expected_call))

    @patch('xivo_call_logs.raw_call_log.RawCallLog')
    def test_call_logs_from_cel_two_calls(self, raw_call_log_constructor):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1, call_2 = self.interpretor.interpret_cels.side_effect \
                       = raw_call_log_constructor.side_effect \
                       = [Mock(), Mock()]
        expected_call_1 = call_1.to_call_log.return_value
        expected_call_2 = call_2.to_call_log.return_value

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_any_call(cels_1, ANY)
        self.interpretor.interpret_cels.assert_any_call(cels_2, ANY)
        assert_that(result, contains_inanyorder(expected_call_1, expected_call_2))

    @patch('xivo_call_logs.raw_call_log.RawCallLog')
    def test_call_logs_from_cel_two_calls_one_valid_one_invalid(self, raw_call_log_constructor):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1, call_2 = self.interpretor.interpret_cels.side_effect \
                       = raw_call_log_constructor.side_effect \
                       = [Mock(), Mock()]
        expected_call_1 = call_1.to_call_log.return_value
        call_2.to_call_log.side_effect = InvalidCallLogException()

        result = self.generator.call_logs_from_cel(cels)

        self.interpretor.interpret_cels.assert_any_call(cels_1, ANY)
        self.interpretor.interpret_cels.assert_any_call(cels_2, ANY)
        assert_that(result, contains(expected_call_1))

    def test_list_call_log_ids(self):
        cel_1, cel_2 = Mock(call_log_id=1), Mock(call_log_id=1)
        cel_3, cel_4 = Mock(call_log_id=2), Mock(call_log_id=None)
        cels = [cel_1, cel_2, cel_3, cel_4]

        result = self.generator.list_call_log_ids(cels)

        assert_that(result, contains_inanyorder(1, 2))

    def test_given_interpretors_can_interpret_then_use_first_interpretor(self):
        interpretor_true_1, interpretor_true_2, interpretor_false = Mock(), Mock(), Mock()
        interpretor_true_1.can_interpret.return_value = True
        interpretor_true_2.can_interpret.return_value = True
        interpretor_false.can_interpret.return_value = False
        generator = CallLogsGenerator([interpretor_false, interpretor_true_1, interpretor_true_2, interpretor_false])
        cels = self._generate_cel_for_call(['545783248'])

        generator.call_logs_from_cel(cels)

        interpretor_true_1.interpret_cels.assert_called_once_with(cels, ANY)
        assert_that(interpretor_true_2.interpret_cels.called, is_(False))
        assert_that(interpretor_false.interpret_cels.called, is_(False))

    def test_given_no_interpretor_can_interpret_then_raise(self):
        interpretor = Mock()
        interpretor.can_interpret.return_value = False
        generator = CallLogsGenerator([interpretor])
        cels = self._generate_cel_for_call(['545783248'])

        assert_that(calling(generator.call_logs_from_cel).with_args(cels), raises(RuntimeError))

    def _generate_cel_for_call(self, linked_id, cel_count=3):
        result = []
        for _ in range(cel_count):
            result.append(Mock(linkedid=linked_id))

        return result
