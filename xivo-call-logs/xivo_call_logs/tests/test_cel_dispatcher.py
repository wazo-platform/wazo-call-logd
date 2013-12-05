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


from hamcrest import assert_that, contains, equal_to, same_instance
from mock import Mock, patch, sentinel
from unittest import TestCase

from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.raw_call_log import RawCallLog
from xivo_dao.data_handler.call_log.model import CallLog


class TestCELDispatcher(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = Mock()
        self.callee_cel_interpretor = Mock()
        self.cel_dispatcher = CELDispatcher(self.caller_cel_interpretor,
                                            self.callee_cel_interpretor)

    def tearDown(self):
        pass

    def test_interpret_call(self):
        cels = [Mock(), Mock()]
        raw_call_log = Mock(RawCallLog)
        expected_call_log = raw_call_log.to_call_log.return_value = Mock(CallLog)
        self.cel_dispatcher.interpret_cels = Mock(return_value=raw_call_log)

        result = self.cel_dispatcher.interpret_call(cels)

        self.cel_dispatcher.interpret_cels.assert_called_once_with(cels)
        assert_that(result, equal_to(expected_call_log))

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
        cels = cel_1, cel_2, cel_3 = \
            [Mock(uniqueid=1, eventtype='CHAN_START'),
             Mock(uniqueid=2, eventtype='CHAN_START'),
             Mock(uniqueid=3, eventtype='CHAN_START')]

        result = self.cel_dispatcher.split_caller_callee_cels(cels)

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
        self.cel_dispatcher.split_caller_callee_cels = Mock(return_value=(caller_cels, callee_cels))

        result = self.cel_dispatcher.interpret_cels(cels)

        self.cel_dispatcher.split_caller_callee_cels.assert_called_once_with(cels)
        self.caller_cel_interpretor.interpret_cels.assert_called_once_with(caller_cels, call)
        self.callee_cel_interpretor.interpret_cels.assert_called_once_with(callee_cels, sentinel.call_caller_done)
        assert_that(result, same_instance(sentinel.call_callee_done))
