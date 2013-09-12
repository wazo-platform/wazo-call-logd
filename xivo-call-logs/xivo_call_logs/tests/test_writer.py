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

from mock import Mock, patch
from unittest import TestCase

from xivo_call_logs.generator import CallLogsCreation
from xivo_call_logs.writer import CallLogsWriter


class TestCallLogsWriter(TestCase):
    def setUp(self):
        self.writer = CallLogsWriter()

    def tearDown(self):
        pass

    @patch('xivo_dao.data_handler.call_log.dao.create_from_list')
    @patch('xivo_dao.data_handler.call_log.dao.delete_from_list')
    def test_write(self, mock_dao_delete, mock_dao_create):
        call_logs_creation = CallLogsCreation(new_call_logs=[Mock(), Mock()],
                                              call_logs_to_delete=None)

        self.writer.write(call_logs_creation)

        mock_dao_create.assert_called_once_with(call_logs_creation.new_call_logs)
        mock_dao_delete.assert_called_once_with(call_logs_creation.call_logs_to_delete)
