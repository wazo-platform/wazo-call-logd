# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
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
from hamcrest import all_of, assert_that, equal_to, has_property, is_not, same_instance
from mock import Mock, sentinel
from unittest import TestCase

from xivo_call_logs.cel_interpretor import AbstractCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.raw_call_log import RawCallLog
from xivo_dao.data_handler.cel.event_type import CELEventType
from xivo_dao.data_handler.call_log.model import CallLog


class TestAbstractCELInterpretor(TestCase):

    def setUp(self):

        class ConcreteCELInterpretor(AbstractCELInterpretor):
            def __init__(self):
                self.eventtype_map = {
                    CELEventType.chan_start: self.chan_start,
                    CELEventType.hangup: self.hangup,
                }
            chan_start = Mock()
            hangup = Mock()

        self.cel_interpretor = ConcreteCELInterpretor()

    def tearDown(self):
        pass

    def test_interpret_cels(self):
        cels = cel_1, cel_2, cel_3 = [Mock(id=34), Mock(id=35), Mock(id=36)]
        calls = sentinel.call_1, sentinel.call_2, sentinel.call_3, sentinel.call_4
        self.cel_interpretor.interpret_cel = Mock(side_effect=calls[1:])

        result = self.cel_interpretor.interpret_cels(cels, sentinel.call_1)

        self.cel_interpretor.interpret_cel.assert_any_call(cel_1, sentinel.call_1)
        self.cel_interpretor.interpret_cel.assert_any_call(cel_2, sentinel.call_2)
        self.cel_interpretor.interpret_cel.assert_any_call(cel_3, sentinel.call_3)
        assert_that(result, same_instance(sentinel.call_4))

    def test_interpret_cel_known_events(self):
        self._assert_that_interpret_cel_calls(self.cel_interpretor.chan_start, CELEventType.chan_start)
        self._assert_that_interpret_cel_calls(self.cel_interpretor.hangup, CELEventType.hangup)

    def test_interpret_cel_unknown_events(self):
        cel = Mock(eventtype=CELEventType.answer)

        result = self.cel_interpretor.interpret_cel(cel, sentinel.call)

        assert_that(result, same_instance(sentinel.call))
        assert_that(self.cel_interpretor.chan_start.call_count, equal_to(0))
        assert_that(self.cel_interpretor.hangup.call_count, equal_to(0))

    def _assert_that_interpret_cel_calls(self, function, eventtype):
        cel = Mock(eventtype=eventtype)
        call = Mock(RawCallLog)
        new_call = Mock(RawCallLog)
        function.return_value = new_call

        result = self.cel_interpretor.interpret_cel(cel, call)

        function.assert_called_once_with(cel, call)
        assert_that(result, equal_to(new_call))


class TestCallerCELInterpretor(TestCase):

    def setUp(self):
        self.caller_cel_interpretor = CallerCELInterpretor()

    def tearDown(self):
        pass

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
        line_identity = 'sip/asldfj'
        cel.channame = line_identity + '-0000001'
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, all_of(
            has_property('date', cel_date),
            has_property('source_name', cel_source_name),
            has_property('source_exten', cel_source_exten),
            has_property('destination_exten', cel_destination_exten),
            has_property('source_line_identity', line_identity),
        ))

    def test_interpret_chan_start_with_destination_s(self):
        cel = Mock()
        cel_date = cel.eventtime = datetime.datetime(year=2013, month=1, day=1)
        cel_source_name, cel_source_exten = cel.cid_name, cel.cid_num = 'source_name', 'source_exten'
        cel.exten = 's'
        line_identity = 'sip/asldfj'
        cel.channame = line_identity + '-0000001'
        call = Mock(RawCallLog)

        result = self.caller_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, all_of(
            has_property('date', cel_date),
            has_property('source_name', cel_source_name),
            has_property('source_exten', cel_source_exten),
            has_property('destination_exten', ''),
            has_property('source_line_identity', line_identity),
        ))

    def test_interpret_app_start_no_reverse_lookup(self):
        cel = Mock()
        cel_userfield = cel.userfield = 'userfield'
        cel_cid_name = cel.cid_name = ''
        call = Mock(RawCallLog, source_name='')

        result = self.caller_cel_interpretor.interpret_app_start(cel, call)

        assert_that(result, all_of(
            has_property('user_field', cel_userfield),
            is_not(has_property('cid_name', cel_cid_name))
        ))

    def test_interpret_app_start_reverse_lookup(self):
        cel = Mock()
        cel_userfield = cel.userfield = 'userfield'
        cel_cid_name = cel.cid_name = 'Reversed'
        cel_cid_num = cel.cid_num = 'Reversed'
        call = Mock(RawCallLog, source_name='Original Name')

        result = self.caller_cel_interpretor.interpret_app_start(cel, call)

        assert_that(result, all_of(
            has_property('user_field', cel_userfield),
            has_property('source_name', cel_cid_name),
            has_property('source_exten', cel_cid_num)
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


class TestCalleeCELInterpretor(TestCase):
    def setUp(self):
        self.callee_cel_interpretor = CalleeCELInterpretor()

    def tearDown(self):
        pass

    def test_interpret_chan_start(self):
        cel = Mock()
        line_identity = 'sip/asldfj'
        cel.channame = line_identity + '-0000001'
        call = Mock(RawCallLog)

        result = self.callee_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, has_property('destination_line_identity', line_identity))
