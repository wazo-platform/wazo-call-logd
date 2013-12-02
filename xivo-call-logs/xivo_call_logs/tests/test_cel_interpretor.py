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
from hamcrest import all_of, assert_that, contains, equal_to, has_property, same_instance
from mock import Mock, patch, sentinel
from unittest import TestCase

from xivo_call_logs.cel_interpretor import CELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.raw_call_log import RawCallLog
from xivo_dao.data_handler.cel.event_type import CELEventType
from xivo_dao.data_handler.call_log.model import CallLog


class TestCELInterpretor(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = Mock()
        self.callee_cel_interpretor = Mock()
        self.cel_interpretor = CELInterpretor(self.caller_cel_interpretor,
                                              self.callee_cel_interpretor)

    def tearDown(self):
        pass

    def test_interpret_call(self):
        cels = [Mock(), Mock()]
        raw_call_log = Mock(RawCallLog)
        expected_call_log = raw_call_log.to_call_log.return_value = Mock(CallLog)
        self.cel_interpretor.interpret_cels = Mock(return_value=raw_call_log)

        result = self.cel_interpretor.interpret_call(cels)

        self.cel_interpretor.interpret_cels.assert_called_once_with(cels)
        assert_that(result, equal_to(expected_call_log))

    def test_split_caller_callee_cels_no_cels(self):
        cels = []

        result = self.cel_interpretor.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(), contains()))

    def test_split_caller_callee_cels_1_uniqueid(self):
        cels = cel_1, cel_2 = [Mock(uniqueid=1), Mock(uniqueid=1)]

        result = self.cel_interpretor.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1, cel_2), contains()))

    def test_split_caller_callee_cels_2_uniqueids(self):
        cels = cel_1, cel_2, cel_3, cel_4 = \
            [Mock(uniqueid=1), Mock(uniqueid=2), Mock(uniqueid=1), Mock(uniqueid=2)]

        result = self.cel_interpretor.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1, cel_3),
                                     contains(cel_2, cel_4)))

    def test_split_caller_callee_cels_3_uniqueids(self):
        cels = cel_1, cel_2, cel_3 = \
            [Mock(uniqueid=1), Mock(uniqueid=2), Mock(uniqueid=3)]

        result = self.cel_interpretor.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1),
                                     contains(cel_2)))

    @patch('xivo_call_logs.raw_call_log.RawCallLog')
    def test_interpret_cels(self, mock_raw_call_log):
        cels = cel_1, cel_2, cel_3 = [Mock(id=34), Mock(id=35), Mock(id=36)]
        caller_cels = [cel_1, cel_3]
        callee_cels = [cel_2]
        call = Mock(RawCallLog, id=1)
        mock_raw_call_log.side_effect = [call, Mock(RawCallLog, id=2)]
        self.caller_cel_interpretor.interpret_cels = Mock(return_value=sentinel.call_caller_done)
        self.callee_cel_interpretor.interpret_cels = Mock(return_value=sentinel.call_callee_done)
        self.cel_interpretor.split_caller_callee_cels = Mock(return_value=(caller_cels, callee_cels))

        result = self.cel_interpretor.interpret_cels(cels)

        self.cel_interpretor.split_caller_callee_cels.assert_called_once_with(cels)
        self.caller_cel_interpretor.interpret_cels.assert_called_once_with(caller_cels, call)
        self.callee_cel_interpretor.interpret_cels.assert_called_once_with(callee_cels, sentinel.call_caller_done)
        assert_that(result, same_instance(sentinel.call_callee_done))


class TestCallerCELInterpretor(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = CallerCELInterpretor()

    def tearDown(self):
        pass

    def test_interpret_cels(self):
        cels = cel_1, cel_2, cel_3 = [Mock(id=34), Mock(id=35), Mock(id=36)]
        calls = sentinel.call_1, sentinel.call_2, sentinel.call_3, sentinel.call_4
        self.caller_cel_interpretor.interpret_cel = Mock(side_effect=calls[1:])

        result = self.caller_cel_interpretor.interpret_cels(cels, sentinel.call_1)

        self.caller_cel_interpretor.interpret_cel.assert_any_call(cel_1, sentinel.call_1)
        self.caller_cel_interpretor.interpret_cel.assert_any_call(cel_2, sentinel.call_2)
        self.caller_cel_interpretor.interpret_cel.assert_any_call(cel_3, sentinel.call_3)
        assert_that(result, same_instance(sentinel.call_4))

    def test_interpret_cel(self):
        self.caller_cel_interpretor.interpret_chan_start = Mock()
        self.caller_cel_interpretor.interpret_app_start = Mock()
        self.caller_cel_interpretor.interpret_answer = Mock()
        self.caller_cel_interpretor.interpret_bridge_start = Mock()
        self.caller_cel_interpretor.interpret_hangup = Mock()
        self._assert_that_interpret_cel_calls(self.caller_cel_interpretor.interpret_chan_start, CELEventType.chan_start)
        self._assert_that_interpret_cel_calls(self.caller_cel_interpretor.interpret_app_start, CELEventType.app_start)
        self._assert_that_interpret_cel_calls(self.caller_cel_interpretor.interpret_answer, CELEventType.answer)
        self._assert_that_interpret_cel_calls(self.caller_cel_interpretor.interpret_bridge_start, CELEventType.bridge_start)
        self._assert_that_interpret_cel_calls(self.caller_cel_interpretor.interpret_hangup, CELEventType.hangup)

    def test_interpret_cel_unknown_or_ignored_event(self):
        cel = Mock(eventtype='unknown_or_ignored_eventtype')
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_cel(cel, call)

        assert_that(result, equal_to(call))

    def test_interpret_chan_start(self):
        cel = Mock()
        cel_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        cel_source_name, cel_source_exten = cel.cid_name, cel.cid_num = 'source_name', 'source_exten'
        cel_destination_exten = cel.exten = 'destination_exten'
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, all_of(
            has_property('date', cel_date),
            has_property('source_name', cel_source_name),
            has_property('source_exten', cel_source_exten),
            has_property('destination_exten', cel_destination_exten),
        ))

    def test_interpret_chan_start_with_destination_s(self):
        cel = Mock()
        cel_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        cel_source_name, cel_source_exten = cel.cid_name, cel.cid_num = 'source_name', 'source_exten'
        cel.exten = 's'
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, all_of(
            has_property('date', cel_date),
            has_property('source_name', cel_source_name),
            has_property('source_exten', cel_source_exten),
            has_property('destination_exten', ''),
        ))

    def test_interpret_app_start(self):
        cel = Mock()
        cel_userfield = cel.userfield = 'userfield'
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_app_start(cel, call)

        assert_that(result, all_of(
            has_property('user_field', cel_userfield)
        ))

    def test_interpret_answer_no_destination_yet(self):
        cel = Mock()
        cel_source_name = cel.cid_name = 'destination_exten'
        start_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        call = Mock(RawCallLog, destination_exten=None)

        result = self.caller_cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', cel_source_name),
            has_property('communication_start', start_date),
            has_property('answered', True),
        ))

    def test_interpret_answer_with_destination_already_set(self):
        cel = Mock(cid_name='other_destination')
        start_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        call = Mock(RawCallLog)
        call_destination = call.destination_exten = 'first_destination'

        result = self.caller_cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', call_destination),
            has_property('communication_start', start_date),
            has_property('answered', True),
        ))

    def test_interpret_hangup_sets_call_end(self):
        cel = Mock()
        end_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        call = Mock(CallLog)

        result = self.caller_cel_interpretor.interpret_hangup(cel, call)

        assert_that(result, all_of(
            has_property('communication_end', end_date),
        ))

    def test_interpret_bridge_start_with_no_source_set(self):
        cel = Mock()
        source_name = cel.cid_name = 'source_name'
        source_exten = cel.cid_num = 'source_exten'
        call = Mock(RawCallLog, source_name=None, source_exten=None)

        result = self.caller_cel_interpretor.interpret_bridge_start(cel, call)

        assert_that(result, all_of(
            has_property('source_name', source_name),
            has_property('source_exten', source_exten),
        ))

    def test_interpret_bridge_start_with_source_already_set(self):
        cel = Mock(cid_name='other_source_name', cid_num='other_source_exten')
        call = Mock(RawCallLog)
        source_name = call.source_name = 'first_source_name'
        source_exten = call.source_exten = 'first_source_exten'

        result = self.caller_cel_interpretor.interpret_bridge_start(cel, call)

        assert_that(result, all_of(
            has_property('source_name', source_name),
            has_property('source_exten', source_exten),
        ))

    def _assert_that_interpret_cel_calls(self, function, eventtype):
        cel = Mock(eventtype=eventtype)
        call = Mock(RawCallLog)
        new_call = Mock(RawCallLog)
        function.return_value = new_call

        result = self.caller_cel_interpretor.interpret_cel(cel, call)

        function.assert_called_once_with(cel, call)
        assert_that(result, equal_to(new_call))
