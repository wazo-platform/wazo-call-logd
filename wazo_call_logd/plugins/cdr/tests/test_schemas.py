# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from unittest import TestCase

from hamcrest import assert_that, has_entries

from wazo_call_logd.database.models import CallLog

from ..schemas import CDRSchema


class TestCDRSchemaCallStatus(TestCase):
    def _dump(self, **kwargs):
        call_log = CallLog(date=datetime(2024, 1, 1, 10, 0, 0), **kwargs)
        return CDRSchema().dump(call_log)

    def test_unknown_when_not_answered_not_voicemail_not_blocked(self):
        result = self._dump(date_answer=None, reached_voicemail=False, blocked=False)
        assert_that(result, has_entries(call_status='unknown', answered=False))

    def test_answered_when_date_answer_set(self):
        result = self._dump(
            date_answer=datetime(2024, 1, 1, 10, 0, 5),
            reached_voicemail=False,
            blocked=False,
        )
        assert_that(result, has_entries(call_status='answered', answered=True))

    def test_voicemail_when_reached_voicemail_and_not_answered(self):
        result = self._dump(date_answer=None, reached_voicemail=True, blocked=False)
        assert_that(result, has_entries(call_status='voicemail', answered=False))

    def test_blocked_supersedes_voicemail(self):
        result = self._dump(date_answer=None, reached_voicemail=True, blocked=True)
        assert_that(result, has_entries(call_status='blocked'))
