# Copyright 2021-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, equal_to, has_entry, has_key, has_properties
from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import USER_1_TOKEN as TOKEN_SUB_TENANT
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


class TestConfig(IntegrationTest):
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def test_get(self):
        result = self.call_logd.config.get()
        assert_that(result, has_key('rest_api'))

    def test_restrict_only_master_tenant(self):
        with self.set_token(TOKEN_SUB_TENANT):
            assert_that(
                calling(self.call_logd.config.get),
                raises(CallLogdError, has_properties(status_code=401)),
            )

        with self.set_token(TOKEN_SUB_TENANT):
            assert_that(
                calling(self.call_logd.config.patch).with_args({}),
                raises(CallLogdError, has_properties(status_code=401)),
            )

    def test_restrict_when_service_token_not_initialized(self):
        def _returns_503():
            assert_that(
                calling(self.call_logd.config.get),
                raises(
                    CallLogdError,
                    has_properties(
                        status_code=503,
                        error_id='not-initialized',
                    ),
                ),
            )

        config = {'auth': {'username': 'invalid-service', 'master_tenant_uuid': ''}}
        with self.call_logd_with_config(config):
            until.assert_(_returns_503, tries=10)

    def test_update_config(self):
        debug_true_config = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': True,
            }
        ]
        debug_false_config = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': False,
            }
        ]

        debug_true_patched_config = self.call_logd.config.patch(debug_true_config)
        debug_true_config = self.call_logd.config.get()
        assert_that(debug_true_config, has_entry('debug', True))
        assert_that(debug_true_patched_config, equal_to(debug_true_config))

        debug_false_patched_config = self.call_logd.config.patch(debug_false_config)
        debug_false_config = self.call_logd.config.get()
        assert_that(debug_false_config, has_entry('debug', False))
        assert_that(debug_false_patched_config, equal_to(debug_false_config))
