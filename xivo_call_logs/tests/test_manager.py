# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from mock import Mock

from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.writer import CallLogsWriter
from xivo_call_logs.bus_publisher import BusPublisher


class TestCallLogsManager(TestCase):
    def setUp(self):
        self.cel_fetcher = Mock(CELFetcher)
        self.generator = Mock(CallLogsGenerator)
        self.writer = Mock(CallLogsWriter)
        self.publisher = Mock(BusPublisher)
        self.manager = CallLogsManager(self.cel_fetcher, self.generator, self.writer, self.publisher)

    def tearDown(self):
        pass

    def test_generate_from_count(self):
        cel_count = 132456
        cels = self.cel_fetcher.fetch_last_unprocessed.return_value = [Mock(), Mock()]
        call_logs = self.generator.from_cel.return_value = Mock(new_call_logs=[])

        self.manager.generate_from_count(cel_count=cel_count)

        self.cel_fetcher.fetch_last_unprocessed.assert_called_once_with(cel_count)
        self.generator.from_cel.assert_called_once_with(cels)
        self.writer.write.assert_called_once_with(call_logs)

    def test_generate_from_linked_id(self):
        linked_id = '666'
        cels = self.cel_fetcher.fetch_from_linked_id.return_value = [Mock()]
        call_logs = self.generator.from_cel.return_value = Mock(new_call_logs=[])

        self.manager.generate_from_linked_id(linked_id=linked_id)

        self.cel_fetcher.fetch_from_linked_id.assert_called_once_with(linked_id)
        self.generator.from_cel.assert_called_once_with(cels)
        self.writer.write.assert_called_once_with(call_logs)
