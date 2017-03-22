# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os

from contextlib import contextmanager
from requests.packages import urllib3
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase

urllib3.disable_warnings()


class IntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
    service = 'call-logd'

    @contextmanager
    def auth_stopped(self):
        self.stop_service('auth')
        yield
        self.start_service('auth')
