# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, contains, has_entries, has_properties
from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    OTHER_TENANT,
    UNKNOWN_UUID,
)
from .helpers.database import RetentionData, retention
from .helpers.wait_strategy import CallLogdComponentsWaitStrategy


class TestRetention(IntegrationTest):
    wait_strategy = CallLogdComponentsWaitStrategy(["bus_consumer"])

    @retention(cdr_days=2, export_days=4, recording_days=2)
    def test_get(self, retention: RetentionData):
        result = self.call_logd.retention.get(tenant_uuid=str(MASTER_TENANT))
        assert_that(
            result,
            has_entries(
                tenant_uuid=str(MASTER_TENANT),
                cdr_days=2,
                export_days=4,
                recording_days=2,
                default_cdr_days=365,
                default_export_days=2,
                default_recording_days=365,
            ),
        )

    def test_get_not_configured_tenant(self):
        result = self.call_logd.retention.get(tenant_uuid=str(OTHER_TENANT))
        assert_that(
            result,
            has_entries(
                tenant_uuid=str(OTHER_TENANT),
                cdr_days=None,
                export_days=None,
                recording_days=None,
                default_cdr_days=365,
                default_export_days=2,
                default_recording_days=365,
            ),
        )

    def test_get_unknown_tenant(self):
        assert_that(
            calling(self.call_logd.retention.get).with_args(
                tenant_uuid=str(UNKNOWN_UUID)
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=401, error_id='unauthorized-tenant')
            ),
        )

    @retention()
    def test_update(self, retention: RetentionData):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
        tenant = str(retention['tenant_uuid'])
        self.call_logd.retention.update(**args, tenant_uuid=tenant)

        result = self.call_logd.retention.get(tenant_uuid=str(MASTER_TENANT))
        assert_that(result, has_entries(**args))

    def test_update_not_configured(self):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
        self.call_logd.retention.update(**args, tenant_uuid=str(OTHER_TENANT))

        result = self.call_logd.retention.get(tenant_uuid=str(OTHER_TENANT))
        assert_that(result, has_entries(**args))

    def test_update_unknown_tenant(self):
        assert_that(
            calling(self.call_logd.retention.update).with_args(
                tenant_uuid=str(UNKNOWN_UUID)
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=401, error_id='unauthorized-tenant')
            ),
        )

    @retention()
    def test_update_errors(self, retention: RetentionData):
        args = {'cdr_days': 1, 'recording_days': 2}
        assert_that(
            calling(self.call_logd.retention.update).with_args(
                **args, tenant_uuid=str(retention['tenant_uuid'])
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='invalid-data')
            ),
        )

    @retention()
    def test_update_events(self, retention: RetentionData):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
        events = self.bus.accumulator(headers={'name': 'call_logd_retention_updated'})

        tenant = str(retention['tenant_uuid'])
        self.call_logd.retention.update(**args, tenant_uuid=tenant)

        result = self.call_logd.retention.get(tenant_uuid=str(MASTER_TENANT))
        assert_that(result, has_entries(**args))

        # TODO(fblackburn) code should publish event BEFORE returning HTTP response
        def event_received():
            assert_that(
                events.accumulate(with_headers=True),
                contains(
                    has_entries(
                        message=has_entries(
                            data=has_entries(**args),
                        ),
                        headers=has_entries(
                            name='call_logd_retention_updated',
                            required_acl='events.call_logd.retention.updated',
                            tenant_uuid=tenant,
                        ),
                    ),
                ),
            )

        until.assert_(event_received, tries=3)
