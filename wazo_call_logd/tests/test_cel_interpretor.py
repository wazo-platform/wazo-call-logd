# Copyright 2013-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import datetime

from unittest import TestCase
from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from hamcrest import has_property
from hamcrest import has_properties
from hamcrest import none
from hamcrest import same_instance
from mock import Mock
from mock import sentinel
from xivo_dao.resources.cel.event_type import CELEventType
from xivo_dao.alchemy.call_log import CallLog

from wazo_call_logd.cel_interpretor import AbstractCELInterpretor
from wazo_call_logd.cel_interpretor import CallerCELInterpretor
from wazo_call_logd.cel_interpretor import CalleeCELInterpretor
from wazo_call_logd.cel_interpretor import DispatchCELInterpretor
from wazo_call_logd.cel_interpretor import find_participant
from wazo_call_logd.raw_call_log import RawCallLog


def confd_mock(lines=None):
    lines = lines or []
    confd = Mock()
    confd.lines.list.return_value = {'items': lines}
    confd.users.get.return_value = lines[0]['users'][0] if lines and lines[0]['users'] else None
    return confd


class TestFindParticipant(TestCase):

    def test_find_participants_when_channame_is_not_parsable(self):
        confd = confd_mock()
        channame = 'something'

        result = find_participant(confd, channame, role='source')

        assert_that(result, none())

    def test_find_participants_when_no_lines(self):
        confd = confd_mock()
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame, role='source')

        assert_that(result, none())

    def test_find_participants_when_line_has_no_user(self):
        lines = [{'id': 12, 'users': []}]
        confd = confd_mock(lines)
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame, role='source')

        assert_that(result, none())

    def test_find_participants_when_line_has_user(self):
        user = {'uuid': 'user_uuid', 'userfield': 'user_userfield, toto'}
        lines = [{'id': 12, 'users': [user]}]
        confd = confd_mock(lines)
        channame = 'sip/something-suffix'

        result = find_participant(confd, channame, role='source')

        assert_that(result, has_properties(role='source',
                                           user_uuid='user_uuid',
                                           line_id=12,
                                           tags=['user_userfield', 'toto']))


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
        cels = cel_1, cel_2, cel_3 = [
            Mock(uniqueid=1, eventtype='CHAN_START'),
            Mock(uniqueid=2, eventtype='CHAN_START'),
            Mock(uniqueid=3, eventtype='CHAN_START'),
        ]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

        assert_that(result, contains(contains(cel_1),
                                     contains(cel_2, cel_3)))


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
