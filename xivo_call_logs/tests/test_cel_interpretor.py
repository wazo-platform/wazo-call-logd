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

import datetime

from unittest import TestCase
from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from hamcrest import has_property
from hamcrest import same_instance
from mock import Mock
from mock import sentinel
from xivo_dao.resources.cel.event_type import CELEventType
from xivo_dao.resources.call_log.model import CallLog

from xivo_call_logs.cel_interpretor import AbstractCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.raw_call_log import RawCallLog


def confd_mock():
    confd = Mock()
    confd.lines.list.return_value = {'items': []}
    return confd


class TestCELDispatcher(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = Mock()
        self.callee_cel_interpretor = Mock()
        self.cel_dispatcher = DispatchCELInterpretor(self.caller_cel_interpretor,
                                                     self.callee_cel_interpretor)

    def test_split_caller_callee_cels_no_cels(self):
        cels = []

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(), contains()))

    def test_split_caller_callee_cels_1_uniqueid(self):
        cels = cel_1, cel_2 = [Mock(uniqueid=1, eventtype='CHAN_START'),
                               Mock(uniqueid=1, eventtype='APP_START')]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1, cel_2), contains()))

    def test_split_caller_callee_cels_2_uniqueids(self):
        cels = cel_1, cel_2, cel_3, cel_4 = \
            [Mock(uniqueid=1, eventtype='CHAN_START'),
             Mock(uniqueid=2, eventtype='CHAN_START'),
             Mock(uniqueid=1, eventtype='APP_START'),
             Mock(uniqueid=2, eventtype='ANSWER')]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1, cel_3),
                                     contains(cel_2, cel_4)))

    def test_split_caller_callee_cels_3_uniqueids(self):
        cels = cel_1, cel_2, _ = [
            Mock(uniqueid=1, eventtype='CHAN_START'),
            Mock(uniqueid=2, eventtype='CHAN_START'),
            Mock(uniqueid=3, eventtype='CHAN_START'),
        ]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1),
                                     contains(cel_2)))


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
        self.caller_cel_interpretor = CallerCELInterpretor(confd_mock())

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

    def test_interpret_app_start_when_cid_name_num_are_empty_then_do_not_change_source_name_exten(self):
        cel = Mock()
        cel_userfield = cel.userfield = 'userfield'
        cel.cid_name = ''
        cel.cid_num = ''
        call = Mock(RawCallLog, source_name=sentinel.original_name)

        result = self.caller_cel_interpretor.interpret_app_start(cel, call)

        assert_that(result, all_of(
            has_property('user_field', cel_userfield),
            has_property('source_name', sentinel.original_name)
        ))

    def test_interpret_app_start_when_cid_name_then_replace_source_name(self):
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
        cel = Mock(cid_name=sentinel.destination_exten)
        call = Mock(RawCallLog, destination_exten=None)

        result = self.caller_cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', sentinel.destination_exten),
        ))

    def test_interpret_answer_with_destination_already_set(self):
        cel = Mock(cid_name=sentinel.other_destination)
        call = Mock(RawCallLog, destination_exten=sentinel.original_destination)

        result = self.caller_cel_interpretor.interpret_answer(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', sentinel.original_destination),
        ))

    def test_interpret_bridge_end_or_exit_sets_call_end(self):
        end_date = datetime.datetime(year=2013, month=1, day=1)
        cel = Mock(eventtime=end_date)
        call = Mock(CallLog)

        result = self.caller_cel_interpretor.interpret_bridge_end_or_exit(cel, call)

        assert_that(result, all_of(
            has_property('communication_end', end_date),
        ))

    def test_interpret_bridge_start_or_enter_with_no_source_set(self):
        cel = Mock(
            cid_name=sentinel.source_name,
            cid_num=sentinel.source_exten,
        )
        call = Mock(RawCallLog, source_name=None, source_exten=None)

        result = self.caller_cel_interpretor.interpret_bridge_start_or_enter(cel, call)

        assert_that(result, all_of(
            has_property('source_name', sentinel.source_name),
            has_property('source_exten', sentinel.source_exten),
        ))

    def test_interpret_bridge_start_or_enter_sets_communication_start(self):
        cel = Mock(
            eventtime=sentinel.eventtime,
            cid_name=sentinel.name,
            cid_num=sentinel.exten,
        )
        call = Mock(RawCallLog, source_name=None, source_exten=None)

        result = self.caller_cel_interpretor.interpret_bridge_start_or_enter(cel, call)

        assert_that(result, all_of(
            has_property('communication_start', sentinel.eventtime),
            has_property('answered', True),
        ))

    def test_interpret_bridge_start_or_enter_with_source_already_set(self):
        cel = Mock(cid_name=sentinel.other_source_name,
                   cid_num=sentinel.other_source_exten)
        call = Mock(RawCallLog,
                    source_name=sentinel.first_source_name,
                    source_exten=sentinel.first_source_exten)

        result = self.caller_cel_interpretor.interpret_bridge_start_or_enter(cel, call)

        assert_that(result, all_of(
            has_property('source_name', sentinel.first_source_name),
            has_property('source_exten', sentinel.first_source_exten),
        ))

    def test_interpret_xivo_from_s(self):
        exten = '1002'
        cel = Mock(exten=exten)
        call = Mock(CallLog)

        result = self.caller_cel_interpretor.interpret_xivo_from_s(cel, call)

        assert_that(result, all_of(
            has_property('destination_exten', '1002'),
        ))


class TestCalleeCELInterpretor(TestCase):

    def setUp(self):
        self.callee_cel_interpretor = CalleeCELInterpretor(confd_mock())

    def test_interpret_chan_start(self):
        line_identity = 'sip/asldfj'
        cel = Mock(channame=line_identity + '-0000001')
        call = Mock(RawCallLog)

        result = self.callee_cel_interpretor.interpret_chan_start(cel, call)

        assert_that(result, has_property('destination_line_identity', line_identity))
