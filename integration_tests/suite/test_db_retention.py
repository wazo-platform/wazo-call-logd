# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid

from hamcrest import (
    assert_that,
    equal_to,
    has_properties,
    none,
)

from wazo_call_logd.database.models import Retention

from .helpers.base import DBIntegrationTest
from .helpers.database import retention
from .helpers.constants import UNKNOWN_UUID, MASTER_TENANT


class TestRecording(DBIntegrationTest):
    def test_find_or_create(self):
        tenant_uuid = uuid.UUID(MASTER_TENANT)
        result = self.dao.retention.find_or_create(tenant_uuid)
        assert_that(result, has_properties(tenant_uuid=tenant_uuid))

        result = self.dao.retention.find_or_create(tenant_uuid)
        assert_that(result, has_properties(tenant_uuid=tenant_uuid))

        result = self.session.query(Retention).count()
        assert_that(result, equal_to(1))

        self.session.query(Retention).delete()
        self.session.commit()

    @retention()
    def test_find(self, retention):
        result = self.dao.retention.find(retention['tenant_uuid'])
        expected = uuid.UUID(retention['tenant_uuid'])
        assert_that(result, has_properties(tenant_uuid=expected))

        result = self.dao.retention.find(UNKNOWN_UUID)
        assert_that(result, none())

    @retention(cdr_days=1, recording_days=1)
    def test_update(self, retention):
        retention = self.dao.retention.find(retention['tenant_uuid'])
        retention.cdr_days = 2
        retention.recording_days = 2
        self.dao.retention.update(retention)

        result = self.dao.retention.find(retention.tenant_uuid)
        assert_that(result, has_properties(cdr_days=2, recording_days=2))