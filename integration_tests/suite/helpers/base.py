# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import pytz
import random

from datetime import datetime
from dateutil.relativedelta import relativedelta
from contextlib import contextmanager, wraps
from requests.packages import urllib3
from hamcrest import assert_that
from wazo_call_logd_client.client import Client as CallLogdClient
from xivo_test_helpers import until
from xivo_test_helpers.auth import AuthClient, MockUserToken
from xivo_test_helpers.wait_strategy import NoWaitStrategy
from xivo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchService,
    NoSuchPort,
)

from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO

from .wait_strategy import CallLogdEverythingUpWaitStrategy
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

CEL_DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}')
DB_URI = os.getenv('DB_URI', 'postgresql://wazo-call-logd:Secr7t@localhost:{port}')


# this decorator takes the output of a psql and changes it into a list of dict
def raw_cels(cel_output):
    cels = []
    lines = cel_output.strip().split('\n')
    columns = [field.strip() for field in lines[0].split('|')]
    for line in lines[2:]:
        cel = [field.strip() for field in line.split('|')]
        cels.append(dict(zip(columns, cel)))

    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cels(cels):
                return func(self, *args, **kwargs)

        return wrapped_function

    return _decorate


def cdr(
    id_=None, caller=None, callee=None, start_time=None, ring_seconds=5, talk_time=30
):
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
            {
                'user_uuid': callee['id'],
                'line_id': caller['line_id'],
                'role': 'destination',
            },
        ],
    }


class WrongClient:
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
        cls.reset_clients()
        cls.wait_strategy.wait(cls)

    def setUp(self):
        super().setUp()
        self.call_logd.set_token(MASTER_TOKEN)

    @classmethod
    def reset_clients(cls):
        cls.call_logd = cls.make_call_logd()
        cls.database = cls.make_database()
        cls.cel_database = cls.make_cel_database()
        cls.auth = cls.make_auth()
        if not isinstance(cls.auth, WrongClient):
            cls.configure_wazo_auth_for_multitenants()

    @classmethod
    def make_call_logd(cls):
        try:
            port = cls.service_port(9298, 'call-logd')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='call-logd')

        return CallLogdClient(
            'localhost',
            port,
            prefix=None,
            https=False,
            token=MASTER_TOKEN,
        )

    @classmethod
    def make_auth(cls):
        try:
            port = cls.service_port(9497, 'auth')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='auth')

        return AuthClient('localhost', port)

    @classmethod
    def make_database(cls):
        try:
            port = cls.service_port(5432, 'postgres')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='database')

        return DbHelper.build(
            'wazo-call-logd',
            'Secr7t',
            'localhost',
            port,
            'wazo-call-logd',
        )

    @classmethod
    def make_cel_database(cls):
        try:
            port = cls.service_port(5432, 'cel-postgres')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='cel_database')

        return DbHelper.build(
            'asterisk',
            'proformatique',
            'localhost',
            port,
            'asterisk',
        )

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

    def _get_tomorrow(self, timezone=None):
        timezone = timezone or pytz.utc
        today = timezone.normalize(timezone.localize(datetime.now()))
        return timezone.normalize(
            timezone.localize(
                datetime(today.year, today.month, today.day) + relativedelta(days=1)
            )
        ).isoformat(timespec='seconds')


class DBIntegrationTest(AssetLaunchingTestCase):

    asset = 'database'
    assets_root = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
    service = 'postgres'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.database = cls.make_database()
        cls.cel_database = cls.make_cel_database()

    @classmethod
    def make_database(cls):
        try:
            port = cls.service_port(5432, 'postgres')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='database')

        return DbHelper.build(
            'wazo-call-logd',
            'Secr7t',
            'localhost',
            port,
            'wazo-call-logd',
        )

    @classmethod
    def make_cel_database(cls):
        try:
            port = cls.service_port(5432, 'cel-postgres')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='cel_database')

        return DbHelper.build(
            'asterisk',
            'proformatique',
            'localhost',
            port,
            'asterisk',
        )

    def setUp(self):
        cel_db_uri = CEL_DB_URI.format(port=self.service_port(5432, 'cel-postgres'))
        CELSession = new_db_session(cel_db_uri)
        db_uri = DB_URI.format(port=self.service_port(5432, 'postgres'))
        Session = new_db_session(db_uri)
        self.dao = DAO(Session, CELSession)
        self.session = Session()
        self.cel_session = CELSession()


class RawCelIntegrationTest(IntegrationTest):

    asset = 'base'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def setUp(self):
        self.bus = self.make_bus()
        self.confd = self.make_confd()
        self.confd.reset()

    @contextmanager
    def cels(self, cels):
        with self.cel_database.queries() as queries:
            for cel in cels:
                cel['id'] = queries.insert_cel(**cel)

        try:
            yield
        finally:
            with self.cel_database.queries() as queries:
                for cel in cels:
                    queries.delete_cel(cel['id'])

    @contextmanager
    def no_call_logs(self):
        with self.cel_database.queries() as queries:
            queries.clear_call_logs()

        yield

        with self.cel_database.queries() as queries:
            queries.clear_call_logs()

    @contextmanager
    def no_recordings(self):
        with self.database.queries() as queries:
            queries.clear_recordings()

        yield

        with self.database.queries() as queries:
            queries.clear_recordings()

    def _assert_last_call_log_matches(self, linkedid, expected):
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_generated():
                with self.cel_database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, expected)

            until.assert_(call_log_generated, tries=5)
