# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from hamcrest import assert_that, equal_to
from mock import patch, Mock

from wazo_call_logd.cel_fetcher import CELFetcher


class TestCELFetcher(TestCase):
    def setUp(self):
        self.cel_fetcher = CELFetcher()

    def tearDown(self):
        pass

    @patch('xivo_dao.resources.cel.dao.find_last_unprocessed')
    def test_fetch_last_unprocessed(self, mock_cel_dao):
        cel_count = 333
        cels = mock_cel_dao.return_value = [Mock(), Mock(), Mock()]

        result = self.cel_fetcher.fetch_last_unprocessed(cel_count)

        mock_cel_dao.assert_called_once_with(cel_count, None)
        assert_that(result, equal_to(cels))

    @patch('xivo_dao.resources.cel.dao.find_from_linked_id')
    def test_find_from_linked_id(self, mock_cel_dao):
        linked_id = '666'
        cels = mock_cel_dao.return_value = [Mock(), Mock(), Mock()]

        result = self.cel_fetcher.fetch_from_linked_id(linked_id)

        mock_cel_dao.assert_called_once_with(linked_id)
        assert_that(result, equal_to(cels))
