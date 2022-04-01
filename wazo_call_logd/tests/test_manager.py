# Copyright 2015-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from mock import Mock

from wazo_call_logd.manager import CallLogsManager
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.writer import CallLogsWriter
from wazo_call_logd.bus import BusPublisher


class TestCallLogsManager(TestCase):
    def setUp(self):
        self.dao = Mock()
        self.generator = Mock(CallLogsGenerator)
        self.writer = Mock(CallLogsWriter)
        self.publisher = Mock(BusPublisher)
        self.manager = CallLogsManager(
            self.dao,
            self.generator,
            self.writer,
            self.publisher,
        )

    def tearDown(self):
        pass

    def test_generate_from_count(self):
        cel_count = 132456
        cels = self.dao.cel.find_last_unprocessed.return_value = [Mock(), Mock()]
        call_logs = self.generator.from_cel.return_value = Mock(new_call_logs=[])

        self.manager.generate_from_count(cel_count=cel_count)

        self.dao.cel.find_last_unprocessed.assert_called_once_with(cel_count)
        self.generator.from_cel.assert_called_once_with(cels)
        self.writer.write.assert_called_once_with(call_logs)

    def test_generate_from_linked_id(self):
        linked_id = '666'
        cels = self.dao.cel.find_from_linked_id.return_value = [Mock()]
        call_logs = self.generator.from_cel.return_value = Mock(new_call_logs=[])

        self.manager.generate_from_linked_id(linked_id=linked_id)

        self.dao.cel.find_from_linked_id.assert_called_once_with(linked_id)
        self.generator.from_cel.assert_called_once_with(cels)
        self.writer.write.assert_called_once_with(call_logs)
