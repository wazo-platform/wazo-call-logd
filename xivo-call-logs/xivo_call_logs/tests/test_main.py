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

from hamcrest import assert_that, equal_to
from mock import Mock, patch
from unittest import TestCase
from xivo_call_logs import main


class TestMain(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse_args(self):
        parser = Mock()

        result = main.parse_args(parser)

        parser.add_argument.assert_called_once_with('-c', '--cel-count',
                                                    default=main.DEFAULT_CEL_COUNT,
                                                    type=int,
                                                    help='Minimum number of CEL entries to process')
        parser.parse_args.assert_called_once_with()
        assert_that(result, equal_to(parser.parse_args.return_value))

    @patch('xivo.pid_file.is_already_running', Mock(return_value=True))
    def test_main_already_running(self):
        main._generate_call_logs = Mock(side_effect=AssertionError('Should not be called'))

        self.assertRaises(SystemExit, main.main)

    @patch('xivo.pid_file.is_already_running', Mock(return_value=False))
    @patch('xivo.pid_file.add_pid_file', Mock())
    def test_main_not_running(self):
        main._generate_call_logs = Mock()

        main.main()

        self.assertEqual(main._generate_call_logs.call_count, 1)

    @patch('xivo.pid_file.is_already_running', Mock(return_value=False))
    @patch('xivo.pid_file.add_pid_file', Mock())
    @patch('xivo.pid_file.remove_pid_file')
    def test_pidfile_removed_on_error(self, mock_remove_pid_file):
        main._generate_call_logs = Mock()

        main.main()

        self.assertEqual(mock_remove_pid_file.call_count, 1)
