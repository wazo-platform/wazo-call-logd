# Copyright 2021-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains,
    empty,
    has_entries,
    has_properties,
)
from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    OTHER_TENANT,
    UNKNOWN_UUID,
)
from .helpers.database import retention


class TestRetention(IntegrationTest):
    @retention(cdr_days=2, export_days=4, recording_days=2)
    def test_get(self, retention):
        result = self.call_logd.retention.get(tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                tenant_uuid=MASTER_TENANT,
                cdr_days=2,
                export_days=4,
                recording_days=2,
                default_cdr_days=365,
                default_export_days=2,
                default_recording_days=365,
            ),
        )

    def test_get_not_configured_tenant(self):
        result = self.call_logd.retention.get(tenant_uuid=OTHER_TENANT)
        assert_that(
            result,
            has_entries(
                tenant_uuid=OTHER_TENANT,
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
            calling(self.call_logd.retention.get).with_args(tenant_uuid=UNKNOWN_UUID),
            raises(CallLogdError).matching(
                has_properties(status_code=401, error_id='unauthorized-tenant')
            ),
        )

    @retention()
    def test_update(self, retention):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
        tenant = retention['tenant_uuid']
        self.call_logd.retention.update(**args, tenant_uuid=tenant)

        result = self.call_logd.retention.get(tenant_uuid=MASTER_TENANT)
        assert_that(result, has_entries(**args))

    def test_update_not_configured(self):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
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

    @retention()
    def test_update_errors(self, retention):
        args = {'cdr_days': 1, 'recording_days': 2}
        assert_that(
            calling(self.call_logd.retention.update).with_args(
                **args, tenant_uuid=retention['tenant_uuid']
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='invalid-data')
            ),
        )

    @retention()
    def test_update_events(self, retention):
        args = {'cdr_days': 2, 'export_days': 3, 'recording_days': 2}
        events = self.bus.accumulator(headers={'name': 'call_logd_retention_updated'})

        tenant = retention['tenant_uuid']
        self.call_logd.retention.update(**args, tenant_uuid=tenant)

        result = self.call_logd.retention.get(tenant_uuid=MASTER_TENANT)
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

    @retention()
    def test_tenant_cleanup(self, retention: dict):
        self.bus.send_tenant_deleted(retention['tenant_uuid'])

        def assert_no_retention_for_tenant():
            with self.database.queries() as queries:
                retentions = queries.find_retentions(
                    tenant_uuid=retention['tenant_uuid']
                )
                assert_that(retentions, empty())

        until.assert_(assert_no_retention_for_tenant, tries=5)
