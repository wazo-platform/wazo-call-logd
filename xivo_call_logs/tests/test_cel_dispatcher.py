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

from unittest import TestCase

from hamcrest import assert_that, contains, equal_to, same_instance
from mock import Mock, patch, sentinel
from xivo_dao.resources.call_log.model import CallLog

from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.raw_call_log import RawCallLog


class TestCELDispatcher(TestCase):
    def setUp(self):
        self.caller_cel_interpretor = Mock()
        self.callee_cel_interpretor = Mock()
        self.cel_dispatcher = CELDispatcher(self.caller_cel_interpretor,
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
