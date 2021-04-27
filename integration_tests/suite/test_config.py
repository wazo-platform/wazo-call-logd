# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_key,
)

from .helpers.base import IntegrationTest


class TestConfig(IntegrationTest):
    def test_config(self):
        result = self.call_logd.config.get()
        assert_that(result, has_key('rest_api'))
