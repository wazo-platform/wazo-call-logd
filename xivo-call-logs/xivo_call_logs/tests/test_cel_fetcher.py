# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
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
from mock import patch, Mock
from unittest import TestCase

from xivo_call_logs.cel_fetcher import CELFetcher


class TestCELFetcher(TestCase):
    def setUp(self):
        self.cel_fetcher = CELFetcher()

    def tearDown(self):
        pass

    @patch('xivo_dao.data_handler.cel.dao.find_last_unprocessed')
    def test_fetch_last_unprocessed(self, mock_cel_dao):
        cel_count = 333
        cels = mock_cel_dao.return_value = [Mock(), Mock(), Mock()]

        result = self.cel_fetcher.fetch_last_unprocessed(cel_count)

        mock_cel_dao.assert_called_once_with(cel_count)
        assert_that(result, equal_to(cels))
