# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import requests

from contextlib import contextmanager
from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import contains_string
from requests.packages import urllib3
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase

urllib3.disable_warnings()


class IntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', 'assets')
    service = 'call-logd'

    @classmethod
    @contextmanager
    def auth_stopped(cls):
        cls.stop_service('auth')
        yield
        cls.start_service('auth')


class TestNoAuth(IntegrationTest):

    asset = 'base'

    def test_given_no_auth_when_list_cdr_then_503(self):
        with self.auth_stopped():
            result = requests.get('https://localhost:9298/1.0/cdr', verify=False)

            assert_that(result.status_code, equal_to(503))
            assert_that(result.json()['message'].lower(), contains_string('auth'))

    def test_given_no_token_when_list_cdr_then_401(self):
        result = requests.get('https://localhost:9298/1.0/cdr', verify=False)

        assert_that(result.status_code, equal_to(401))
        assert_that(result.json()['message'].lower(), contains_string('unauthorized'))
