# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from ..extension_filter import ExtensionFilter


class MockRawCall:
    def __init__(self, init_exten):
        self.source_exten = init_exten
        self.source_internal_exten = init_exten
        self.requested_exten = init_exten
        self.requested_internal_exten = init_exten
        self.destination_exten = init_exten
        self.destination_internal_exten = init_exten


class TestExtensionFilter(TestCase):
    def test_filter_empty(self):
        filter = ExtensionFilter([])
        assert filter.filter('') == ''
        assert filter.filter('s') == 's'
        assert filter.filter('test') == 'test'

    def test_filter_default(self):
        filter = ExtensionFilter(['s'])
        assert filter.filter('') == ''
        assert filter.filter('s') == ''
        assert filter.filter('test') == 'test'

    def test_filter_explicit(self):
        filter = ExtensionFilter()
        filter.add_exten('s')
        assert filter.filter('') == ''
        assert filter.filter('s') == ''
        assert filter.filter('test') == 'test'

    def test_filter_call(self):
        filter = ExtensionFilter()
        filter.add_exten('s')

        call_empty = MockRawCall('')
        filter.filter_call(call_empty)
        assert call_empty.source_exten == ''
        assert call_empty.source_internal_exten == ''
        assert call_empty.requested_exten == ''
        assert call_empty.requested_internal_exten == ''
        assert call_empty.destination_exten == ''
        assert call_empty.destination_internal_exten == ''

        call_s = MockRawCall('s')
        filter.filter_call(call_s)
        assert call_s.source_exten == ''
        assert call_s.source_internal_exten == ''
        assert call_s.requested_exten == ''
        assert call_s.requested_internal_exten == ''
        assert call_s.destination_exten == ''
        assert call_s.destination_internal_exten == ''

        call_test = MockRawCall('test')
        filter.filter_call(call_test)
        assert call_test.source_exten == 'test'
        assert call_test.source_internal_exten == 'test'
        assert call_test.requested_exten == 'test'
        assert call_test.requested_internal_exten == 'test'
        assert call_test.destination_exten == 'test'
        assert call_test.destination_internal_exten == 'test'
