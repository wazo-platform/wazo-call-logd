# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    has_key,
    has_properties,
)
from xivo_test_helpers.hamcrest.raises import raises
from wazo_call_logd_client.exceptions import CallLogdError

from .helpers.base import IntegrationTest
from .helpers.constants import USER_1_TOKEN as TOKEN_SUB_TENANT


class TestConfig(IntegrationTest):
    def test_get(self):
        result = self.call_logd.config.get()
        assert_that(result, has_key('rest_api'))

    def test_restrict_only_master_tenant(self):
        with self.set_token(TOKEN_SUB_TENANT):
            assert_that(
                calling(self.call_logd.config.get),
                raises(CallLogdError, has_properties(status_code=401)),
            )
