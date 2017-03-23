# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import empty
from hamcrest import has_entry
from hamcrest import has_properties
from xivo_call_logs_client.exceptions import CallLogdError

from .test_api.base import IntegrationTest
from .test_api.constants import VALID_TOKEN
from .test_api.hamcrest.raises import raises
from .test_api.hamcrest.contains_string_ignoring_case import contains_string_ignoring_case


class TestNoAuth(IntegrationTest):

    asset = 'base'

    def test_given_no_auth_when_list_cdr_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.cdr.list),
                raises(CallLogdError).matching(has_properties(status_code=503,
                                                              message=contains_string_ignoring_case('auth')))
            )

    def test_given_no_token_when_list_cdr_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list),
            raises(CallLogdError).matching(has_properties(status_code=401,
                                                          message=contains_string_ignoring_case('unauthorized')))
        )
        self.call_logd.set_token(VALID_TOKEN)


class TestListCDR(IntegrationTest):

    asset = 'base'

    def test_given_no_call_logs_when_list_cdr_then_empty_list(self):
        result = self.call_logd.cdr.list()

        assert_that(result, has_entry('items', empty()))
