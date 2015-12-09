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

from unittest import TestCase

from hamcrest import assert_that, equal_to
from mock import Mock

from xivo_call_logs.bin import main


class TestMain(TestCase):

    def test_parse_args(self):
        parser = Mock()

        result = main.parse_args(parser)

        parser.add_argument.assert_called_once_with('-c', '--cel-count',
                                                    default=main.DEFAULT_CEL_COUNT,
                                                    type=int,
                                                    help='Minimum number of CEL entries to process')
        parser.parse_args.assert_called_once_with()
        assert_that(result, equal_to(parser.parse_args.return_value))
