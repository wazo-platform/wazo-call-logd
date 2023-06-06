# Copyright 2013-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock, patch

from hamcrest import all_of, assert_that, equal_to, has_property

from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd.raw_call_log import RawCallLog


@patch('wazo_call_logd.raw_call_log.CallLog', Mock)
class TestRawCallLog(TestCase):
    def setUp(self):
        self.raw_call_log = RawCallLog()

    def test_to_call_log(self):
        self.raw_call_log.date = Mock()
        self.raw_call_log.date_answer = Mock()
        self.raw_call_log.date_end = Mock()
        self.raw_call_log.source_name = Mock()
        self.raw_call_log.source_exten = Mock()
        self.raw_call_log.destination_name = Mock()
        self.raw_call_log.destination_exten = Mock()
        self.raw_call_log.user_field = Mock()
        self.raw_call_log.cel_ids = [1, 2, 3]

        result = self.raw_call_log.to_call_log()

        assert_that(
            result,
            all_of(
                has_property('date', self.raw_call_log.date),
                has_property('date_answer', self.raw_call_log.date_answer),
                has_property('date_end', self.raw_call_log.date_end),
                has_property('source_name', self.raw_call_log.source_name),
                has_property('source_exten', self.raw_call_log.source_exten),
                has_property('destination_name', self.raw_call_log.destination_name),
                has_property('destination_exten', self.raw_call_log.destination_exten),
                has_property('user_field', self.raw_call_log.user_field),
            ),
        )
        assert_that(result.cel_ids, equal_to([1, 2, 3]))

    def test_to_call_log_invalid_date(self):
        self.raw_call_log.date = None

        self.assertRaises(InvalidCallLogException, self.raw_call_log.to_call_log)

    def test_to_call_log_with_no_source(self):
        self.raw_call_log.source_name = ''
        self.raw_call_log.source_exten = ''

        self.assertRaises(InvalidCallLogException, self.raw_call_log.to_call_log)
