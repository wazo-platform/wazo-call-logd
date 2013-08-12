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

from hamcrest import assert_that, contains, equal_to
from mock import Mock
from unittest import TestCase

from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.cel_interpretor import CELInterpretor


class TestCallLogsGenerator(TestCase):
    def setUp(self):
        self.cel_interpretor = Mock(CELInterpretor)
        self.generator = CallLogsGenerator(self.cel_interpretor)

    def tearDown(self):
        pass

    def test_from_cel_no_cels(self):
        cels = []

        result = self.generator.from_cel(cels)

        assert_that(result, equal_to([]))

    def test_from_cel_one_call(self):
        linkedid = '9328742934'
        cels = self._generate_cel_for_call([linkedid])
        call = self.cel_interpretor.interpret_call.return_value = Mock()

        result = self.generator.from_cel(cels)

        self.cel_interpretor.interpret_call.assert_called_once_with(cels)
        assert_that(result, contains(call))

    def test_from_cel_two_calls(self):
        cels_1 = self._generate_cel_for_call('9328742934')
        cels_2 = self._generate_cel_for_call('2707230959')
        cels = cels_1 + cels_2
        call_1, call_2 = self.cel_interpretor.interpret_call.side_effect = [Mock(), Mock()]

        result = self.generator.from_cel(cels)

        self.cel_interpretor.interpret_call.assert_any_call(cels_1)
        self.cel_interpretor.interpret_call.assert_any_call(cels_2)
        assert_that(result, contains(call_1, call_2))

    def _generate_cel_for_call(self, linked_id, cel_count=3):
        result = []
        for _ in range(cel_count):
            result.append(Mock(linkedid=linked_id))

        return result
