# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import requests
import yaml

from openapi_spec_validator import validate_v2_spec

from .helpers.base import IntegrationTest

logger = logging.getLogger('openapi_spec_validator')
logger.setLevel(logging.INFO)


class TestDocumentation(IntegrationTest):

    asset = 'documentation'

    def test_documentation_errors(self):
        port = self.service_port(9298, 'call-logd')
        api_url = 'https://localhost:{port}/1.0/api/api.yml'.format(port=port)
        api = requests.get(api_url, verify=False)
        validate_v2_spec(yaml.safe_load(api.text))
