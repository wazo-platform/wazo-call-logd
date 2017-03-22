# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import contains_string

from .test_api.base import IntegrationTest
from .test_api.call_logd import CallLogdClient


class TestNoAuth(IntegrationTest):

    asset = 'base'

    def test_given_no_auth_when_list_cdr_then_503(self):
        ctid_ng = CallLogdClient('localhost', 9298)
        with self.auth_stopped():
            result = ctid_ng.get_cdr_result()

            assert_that(result.status_code, equal_to(503))
            assert_that(result.json()['message'].lower(), contains_string('auth'))

    def test_given_no_token_when_list_cdr_then_401(self):
        ctid_ng = CallLogdClient('localhost', 9298)
        result = ctid_ng.get_cdr_result()

        assert_that(result.status_code, equal_to(401))
        assert_that(result.json()['message'].lower(), contains_string('unauthorized'))
