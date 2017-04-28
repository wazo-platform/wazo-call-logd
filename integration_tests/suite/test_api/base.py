# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import tempfile

from contextlib import contextmanager
from requests.packages import urllib3
from xivo_call_logs_client.client import Client as CallLogdClient
from xivo_test_helpers import until
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from xivo_test_helpers.asset_launching_test_case import NoSuchService
from xivo_test_helpers.asset_launching_test_case import NoSuchPort

from .auth import AuthClient
from .bus import CallLogBusClient
from .constants import VALID_TOKEN
from .database import DbHelper

urllib3.disable_warnings()
logger = logging.getLogger(__name__)


class WrongClient(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, member):
        del member
        raise Exception('Could not create client {}'.format(self.name))


class IntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
    service = 'call-logd'

    @classmethod
    def setUpClass(cls):
        super(IntegrationTest, cls).setUpClass()
        try:
            cls.reset_clients()
        except Exception:
            with tempfile.NamedTemporaryFile(delete=False) as logfile:
                logfile.write(cls.log_containers())
                logger.debug('Container logs dumped to %s', logfile.name)
            cls.tearDownClass()
            raise

    @classmethod
    def reset_clients(cls):
        try:
            cls.call_logd = CallLogdClient('localhost',
                                           cls.service_port(9298, 'call-logd'),
                                           verify_certificate=False,
                                           token=VALID_TOKEN)
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.call_logd = WrongClient(name='call-logd')

        try:
            cls.auth = AuthClient('localhost', cls.service_port(9497, 'auth'))
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.auth = WrongClient(name='auth')

        try:
            cls.database = DbHelper.build('asterisk', 'proformatique', 'localhost', cls.service_port(5432, 'postgres'), 'asterisk')
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.call_logd = WrongClient(name='database')

    @classmethod
    def make_bus(cls):
        return CallLogBusClient.from_connection_fields(port=cls.service_port(5672, 'rabbitmq'))

    @contextmanager
    def auth_stopped(self):
        self.stop_service('auth')
        yield
        self.start_service('auth')
        self.reset_clients()
        until.true(self.auth.is_up, tries=5, message='xivo-auth did not come back up')
