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

import datetime
from hamcrest import all_of, assert_that, equal_to, has_property
from mock import Mock, patch
from unittest import TestCase

from xivo_call_logs.cel_interpretor import CELInterpretor
from xivo_dao.data_handler.cel.event_type import CELEventType
from xivo_dao.data_handler.call_log.model import CallLog


class TestCELInterpretor(TestCase):
    def setUp(self):
        self.cel_interpretor = CELInterpretor()

    def tearDown(self):
        pass

    def test_interpret_call(self):
        cels = [Mock(), Mock()]
        filtered_cels = [Mock()]
        expected_call_log = call_log = Mock(CallLog)
        self.cel_interpretor.filter_cels = Mock(return_value=filtered_cels)
        self.cel_interpretor.interpret_cels = Mock(return_value=call_log)

        result = self.cel_interpretor.interpret_call(cels)

        self.cel_interpretor.filter_cels.assert_called_once_with(cels)
        self.cel_interpretor.interpret_cels.assert_called_once_with(filtered_cels)
        assert_that(result, equal_to(expected_call_log))

    def test_filter_cels_no_cels(self):
        cels = []

        result = self.cel_interpretor.filter_cels(cels)

        assert_that(result, equal_to([]))

    def test_filter_cels(self):
        cels = [Mock(uniqueid=1), Mock(uniqueid=2), Mock(uniqueid=1), Mock(uniqueid=3)]
        expected = [cel for cel in cels if cel.uniqueid == 1]

        result = self.cel_interpretor.filter_cels(cels)

        assert_that(result, equal_to(expected))

    @patch('xivo_dao.data_handler.call_log.model.CallLog')
    def test_interpret_cels(self, mock_call_log):
        cels = cel_1, cel_2 = [Mock(), Mock()]
        call = Mock(CallLog, id=1)
        self.cel_interpretor.interpret_cel = Mock(return_value=call)
        mock_call_log.side_effect = [call, Mock(CallLog, id=2)]

        result = self.cel_interpretor.interpret_cels(cels)

        self.cel_interpretor.interpret_cel.assert_any_call(cel_1, call)
        self.cel_interpretor.interpret_cel.assert_any_call(cel_2, call)
        assert_that(self.cel_interpretor.interpret_cel.call_count, equal_to(2))
        assert_that(result, equal_to(call))

    def test_interpret_cel(self):
        self.cel_interpretor.interpret_chan_start = Mock()
        self.cel_interpretor.interpret_answer = Mock()
        self.cel_interpretor.interpret_bridge_start = Mock()
        self.cel_interpretor.interpret_hangup = Mock()
        self.cel_interpretor.interpret_chan_end = Mock()
        self.cel_interpretor.interpret_unknown = Mock()
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_chan_start, CELEventType.chan_start)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_answer, CELEventType.answer)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_bridge_start, CELEventType.bridge_start)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_hangup, CELEventType.hangup)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_chan_end, CELEventType.chan_end)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.interpret_unknown, 'unknown_eventtype')

    def test_interpret_chan_start(self):
        cel = Mock()
        cel_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        cel_source_name, cel_source_exten = cel.cid_name, cel.cid_num = 'source_name', 'source_exten'
        cel_destination_exten = cel.exten = 'destination_exten'
        cel_userfield = cel.userfield = 'userfield'
        call = Mock(CallLog)

        result = self.cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, all_of(
            has_property('date', cel_date),
            has_property('source_name', cel_source_name),
            has_property('source_exten', cel_source_exten),
            has_property('destination_exten', cel_destination_exten),
            has_property('user_field', cel_userfield)
        ))

    def test_interpret_answer_no_destination_yet(self):
        cel = Mock()
        cel_source_name = cel.cid_name = 'destination_exten'
        call = Mock(CallLog, destination_exten=None)

        result = self.cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', cel_source_name),
        ))

    def test_interpret_answer_with_destination_already_set(self):
        cel = Mock(cid_name='other_destination')
        call = Mock(CallLog)
        call_destination = call.destination_exten = 'first_destination'

        result = self.cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', call_destination),
        ))

    def test_interpret_bridge_start_with_no_source_set(self):
        cel = Mock()
        source_name = cel.cid_name = 'source_name'
        source_exten = cel.cid_num = 'source_exten'
        call = Mock(CallLog, source_name=None, source_exten=None)

        result = self.cel_interpretor.interpret_bridge_start(cel, call)

        assert_that(result, all_of(
            has_property('source_name', source_name),
            has_property('source_exten', source_exten),
        ))

    def test_interpret_bridge_start_with_source_already_set(self):
        cel = Mock(cid_name='other_source_name', cid_num='other_source_exten')
        call = Mock(CallLog)
        source_name = call.source_name = 'first_source_name'
        source_exten = call.source_exten = 'first_source_exten'

        result = self.cel_interpretor.interpret_bridge_start(cel, call)

        assert_that(result, all_of(
            has_property('source_name', source_name),
            has_property('source_exten', source_exten),
        ))

    def test_interpret_unknown_does_not_do_anything(self):
        cel = Mock()
        call = Mock()

        self.cel_interpretor.interpret_unknown(cel, call)

    def _assert_that_interpret_cel_calls(self, function, eventtype):
        cel = Mock(eventtype=eventtype)
        call = Mock(CallLog)
        new_call = Mock(CallLog)
        function.return_value = new_call

        result = self.cel_interpretor.interpret_cel(cel, call)

        function.assert_called_once_with(cel, call)
        assert_that(result, equal_to(new_call))
