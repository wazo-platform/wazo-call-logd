# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import random
import tempfile

from contextlib import contextmanager
from requests.packages import urllib3
from wazo_call_logd_client.client import Client as CallLogdClient
from xivo_test_helpers import until
from xivo_test_helpers.auth import AuthClient, MockUserToken
from xivo_test_helpers.wait_strategy import NoWaitStrategy
from xivo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchService,
    NoSuchPort,
)

from .bus import CallLogBusClient
from .confd import ConfdClient
from .constants import (
    MASTER_TENANT,
    MASTER_TOKEN,
    MASTER_USER_UUID,
    NOW,
    OTHER_TENANT,
    OTHER_USER_TOKEN,
    OTHER_USER_UUID,
    SECONDS,
    TIME_FORMAT,
    USERS_TENANT,
    USER_1_TOKEN,
    USER_1_UUID,
    USER_2_TOKEN,
    USER_2_UUID,
    WAZO_UUID,
)
from .database import DbHelper

urllib3.disable_warnings()
logger = logging.getLogger(__name__)


def cdr(id_=None, caller=None, callee=None, start_time=None, ring_seconds=5, talk_time=30):
    id_ = id_ or random.randint(1, 999999)
    start_time = start_time or NOW
    answer_time = start_time + ring_seconds * SECONDS
    end_time = answer_time + talk_time * SECONDS

    return {
        'id': id_,
        'date': start_time.strftime(TIME_FORMAT),
        'date_answer': answer_time.strftime(TIME_FORMAT),
        'date_end': end_time.strftime(TIME_FORMAT),
        'destination_exten': callee['exten'],
        'destination_name': callee['name'],
        'destination_internal_exten': callee['exten'],
        'destination_internal_context': callee['context'],
        'direction': 'internal',
        'requested_exten': callee['exten'],
        'requested_internal_exten': callee['exten'],
        'requested_internal_context': callee['context'],
        'source_exten': caller['exten'],
        'source_name': caller['name'],
        'source_internal_exten': caller['exten'],
        'source_internal_context': caller['context'],
        'participants': [
            {'user_uuid': caller['id'], 'line_id': caller['line_id'], 'role': 'source'},
            {'user_uuid': callee['id'], 'line_id': caller['line_id'], 'role': 'destination'},
        ],
    }


class WrongClient(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, member):
        del member
        raise Exception('Could not create client {}'.format(self.name))


class IntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
    service = 'call-logd'
    wait_strategy = NoWaitStrategy()

    @classmethod
    def setUpClass(cls):
        super(IntegrationTest, cls).setUpClass()
        try:
            cls.reset_clients()
            cls.wait_strategy.wait(cls)
        except Exception:
            with tempfile.NamedTemporaryFile(delete=False) as logfile:
                logfile.write(cls.log_containers())
                logger.debug('Container logs dumped to %s', logfile.name)
            cls.tearDownClass()
            raise

    def setUp(self):
        super().setUp()
        self.call_logd.set_token(MASTER_TOKEN)

    @classmethod
    def reset_clients(cls):
        try:
            cls.call_logd = CallLogdClient(
                'localhost',
                cls.service_port(9298, 'call-logd'),
                verify_certificate=False,
                token=MASTER_TOKEN,
            )
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.call_logd = WrongClient(name='call-logd')

        try:
            cls.auth = AuthClient('localhost', cls.service_port(9497, 'auth'))
            cls.configure_wazo_auth_for_multitenants()
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.auth = WrongClient(name='auth')

        try:
            cls.database = DbHelper.build(
                'asterisk',
                'proformatique',
                'localhost',
                cls.service_port(5432, 'postgres'),
                'asterisk',
            )
        except (NoSuchService, NoSuchPort) as e:
            logger.debug(e)
            cls.database = WrongClient(name='database')

    @classmethod
    def make_bus(cls):
        return CallLogBusClient.from_connection_fields(
            port=cls.service_port(5672, 'rabbitmq')
        )

    @classmethod
    def make_confd(cls):
        return ConfdClient('localhost', cls.service_port(9486, 'confd'))

    @contextmanager
    def auth_stopped(self):
        self.stop_service('auth')
        yield
        self.start_service('auth')
        self.reset_clients()
        until.true(self.auth.is_up, tries=5, message='wazo-auth did not come back up')

    @classmethod
    def configure_wazo_auth_for_multitenants(cls):
        # NOTE(sileht): This creates a tenant tree and associated users
        cls.auth.set_token(
            MockUserToken(
                MASTER_TOKEN,
                MASTER_USER_UUID,
                WAZO_UUID,
                {"tenant_uuid": MASTER_TENANT, "uuid": MASTER_USER_UUID},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                USER_1_TOKEN,
                USER_1_UUID,
                WAZO_UUID,
                {"tenant_uuid": USERS_TENANT, "uuid": USER_1_UUID},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                USER_2_TOKEN,
                USER_2_UUID,
                WAZO_UUID,
                {"tenant_uuid": USERS_TENANT, "uuid": USER_2_UUID},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                OTHER_USER_TOKEN,
                OTHER_USER_UUID,
                WAZO_UUID,
                {"tenant_uuid": OTHER_TENANT, "uuid": OTHER_USER_UUID},
            )
        )
        cls.auth.set_tenants(
            {
                'uuid': MASTER_TENANT,
                'name': 'call-logd-tests-master',
                'parent_uuid': MASTER_TENANT,
            },
            {
                'uuid': USERS_TENANT,
                'name': 'call-logd-tests-users',
                'parent_uuid': MASTER_TENANT,
            },
            {
                'uuid': OTHER_TENANT,
                'name': 'call-logd-tests-other',
                'parent_uuid': MASTER_TENANT,
            },
        )
