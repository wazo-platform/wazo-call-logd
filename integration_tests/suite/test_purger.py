# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timedelta as td,
)
from hamcrest import assert_that, has_length

from wazo_call_logd.purger import CallLogsPurger
from wazo_call_logd.database.models import CallLog, Recording

from .helpers.base import DBIntegrationTest
from .helpers.constants import MASTER_TENANT, OTHER_TENANT
from .helpers.database import call_log, recording, retention


class TestPurger(DBIntegrationTest):
    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1))
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=2))
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=3))
    @recording(call_log_id=1)
    @recording(call_log_id=2)
    @recording(call_log_id=3)
    def test_purger(self, *_):
        self._assert_len_call_logs(3)

        days_to_keep = 42
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        self._assert_len_call_logs(3)

        days_to_keep = 2
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        self._assert_len_call_logs(1)

        days_to_keep = 0
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        self._assert_len_call_logs(0)

    def _assert_len_call_logs(self, number):
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(number))
        result = self.session.query(Recording).all()
        assert_that(result, has_length(number))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=2), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 2}, date=dt.utcnow() - td(days=4), tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 3}, date=dt.utcnow() - td(days=2), tenant_uuid=OTHER_TENANT)
    @retention(tenant_uuid=MASTER_TENANT, cdr_days=3)
    def test_purger_by_retention(self, *_):
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(3))

        # When retention < default
        days_to_keep = 365
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(2))

        # When retention > default
        days_to_keep = 1
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(1))

    @call_log(**{'id': 1}, date=dt.utcnow() - td(days=1), tenant_uuid=MASTER_TENANT)
    @retention(tenant_uuid=MASTER_TENANT, cdr_days=0)
    def test_purger_when_retention_is_zero(self, *_):
        days_to_keep = 365
        CallLogsPurger().purge(days_to_keep, self.session)
        self.session.commit()
        result = self.session.query(CallLog).all()
        assert_that(result, has_length(0))
