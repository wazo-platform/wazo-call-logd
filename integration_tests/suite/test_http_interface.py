# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TOKEN
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


class TestHttpInterface(IntegrationTest):
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def test_that_empty_body_returns_400(self):
        port = self.service_port(9298, 'call-logd')
        base_url = f'http://127.0.0.1:{port}/1.0'
        headers = {'X-Auth-Token': MASTER_TOKEN}

        config_url = f'{base_url}/config'
        response = requests.patch(config_url, headers=headers, data='')
        assert response.status_code == 400

        response = requests.patch(config_url, headers=headers, json=None)
        assert response.status_code == 400

        retention_url = f'{base_url}/retention'
        response = requests.put(retention_url, headers=headers, data='')
        assert response.status_code == 400

        response = requests.put(retention_url, headers=headers, json=None)
        assert response.status_code == 400
