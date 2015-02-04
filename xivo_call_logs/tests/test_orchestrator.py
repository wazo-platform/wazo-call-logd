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

from mock import Mock
from unittest import TestCase

from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.orchestrator import CallLogsOrchestrator


class TestCallLogsOrchestrator(TestCase):

    def setUp(self):
        self.bus_client_mock = Mock()
        self.call_logs_manager_mock = Mock(CallLogsManager)
        self.orchestrator = CallLogsOrchestrator(self.bus_client_mock,
                                                 self.call_logs_manager_mock)

    def test_when_run_then_initiate_bus_consumer(self):
        self.orchestrator.run()

        self.bus_client_mock.run.assert_called_once_with(self.call_logs_manager_mock)
