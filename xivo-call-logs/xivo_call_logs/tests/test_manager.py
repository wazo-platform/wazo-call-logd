# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.writer import CallLogsWriter


class TestCallLogsManager(TestCase):
    def setUp(self):
        self.cel_fetcher = Mock(CELFetcher)
        self.generator = Mock(CallLogsGenerator)
        self.writer = Mock(CallLogsWriter)
        self.manager = CallLogsManager(self.cel_fetcher, self.generator, self.writer)

    def tearDown(self):
        pass

    def test_generate_from_count(self):
        cel_count = 132456
        cels = self.cel_fetcher.fetch_last_unprocessed.return_value = [Mock(), Mock()]
        call_logs = self.generator.from_cel.return_value = [Mock(), Mock()]

        self.manager.generate_from_count(cel_count=cel_count)

        self.cel_fetcher.fetch_last_unprocessed.assert_called_once_with(cel_count)
        self.generator.from_cel.assert_called_once_with(cels)
        self.writer.write.assert_called_once_with(call_logs)
