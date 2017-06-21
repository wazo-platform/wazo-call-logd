# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from mock import Mock, patch

from wazo_call_logd.generator import CallLogsCreation
from wazo_call_logd.writer import CallLogsWriter


class TestCallLogsWriter(TestCase):
    def setUp(self):
        self.writer = CallLogsWriter()

    def tearDown(self):
        pass

    @patch('xivo_dao.resources.call_log.dao.create_from_list')
    @patch('xivo_dao.resources.call_log.dao.delete_from_list')
    def test_write(self, mock_dao_delete, mock_dao_create):
        call_logs_creation = CallLogsCreation(new_call_logs=[Mock(), Mock()],
                                              call_logs_to_delete=None)

        self.writer.write(call_logs_creation)

        mock_dao_create.assert_called_once_with(call_logs_creation.new_call_logs)
        mock_dao_delete.assert_called_once_with(call_logs_creation.call_logs_to_delete)
