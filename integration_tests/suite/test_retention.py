# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    has_entries,
    has_properties,
)
from wazo_call_logd_client.exceptions import CallLogdError
from xivo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    OTHER_TENANT,
    UNKNOWN_UUID,
)
from .helpers.database import retention


class TestRetention(IntegrationTest):
    @retention(cdr_days=2, recording_days=2)
    def test_get(self, retention):
        result = self.call_logd.retention.get(tenant_uuid=MASTER_TENANT)
        assert_that(result, has_entries(**retention))

    def test_get_not_configured_tenant(self):
        result = self.call_logd.retention.get(tenant_uuid=OTHER_TENANT)
        assert_that(
            result,
            has_entries(
                tenant_uuid=OTHER_TENANT,
                cdr_days=None,
                recording_days=None,
            ),
        )

    def test_get_unknown_tenant(self):
        assert_that(
            calling(self.call_logd.retention.get).with_args(tenant_uuid=UNKNOWN_UUID),
            raises(CallLogdError).matching(
                has_properties(status_code=401, error_id='unauthorized-tenant')
            ),
        )

    @retention()
    def test_update(self, retention):
        args = {'cdr_days': 2, 'recording_days': 2}
        tenant = retention['tenant_uuid']
        self.call_logd.retention.update(**args, tenant_uuid=tenant)

        result = self.call_logd.retention.get(tenant_uuid=MASTER_TENANT)
        assert_that(result, has_entries(**args))

    def test_update_not_configured(self):
        args = {'cdr_days': 2, 'recording_days': 2}
        self.call_logd.retention.update(**args, tenant_uuid=OTHER_TENANT)

        result = self.call_logd.retention.get(tenant_uuid=OTHER_TENANT)
        assert_that(result, has_entries(**args))

    def test_update_unknown_tenant(self):
        assert_that(
            calling(self.call_logd.retention.update).with_args(
                tenant_uuid=UNKNOWN_UUID
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=401, error_id='unauthorized-tenant')
            ),
        )
