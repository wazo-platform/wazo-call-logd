# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import random
from contextlib import contextmanager, wraps
from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta
from hamcrest import assert_that
from requests.packages import urllib3
from wazo_call_logd_client.client import Client as CallLogdClient
from wazo_test_helpers import until
from wazo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchPort,
    NoSuchService,
)
from wazo_test_helpers.auth import AuthClient, MockCredentials, MockUserToken
from wazo_test_helpers.wait_strategy import NoWaitStrategy

from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO

from .bus import CallLogBusClient
from .confd import ConfdClient
from .constants import (
    ALICE,
    BOB,
    EXPORT_SERVICE_ID,
    EXPORT_SERVICE_KEY,
    MASTER_TENANT,
    MASTER_TOKEN,
    MASTER_USER_UUID,
    NOW,
    OTHER_TENANT,
    OTHER_USER_TOKEN,
    OTHER_USER_UUID,
    SECONDS,
    TIME_FORMAT,
    USER_1_TOKEN,
    USER_1_UUID,
    USER_2_TOKEN,
    USER_2_UUID,
    USERS_TENANT,
    WAZO_UUID,
)
from .database import DbHelper
from .email import EmailClient
from .filesystem import FileSystemClient
from .wait_strategy import CallLogdEverythingUpWaitStrategy

urllib3.disable_warnings()
logger = logging.getLogger(__name__)

CEL_DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@127.0.0.1:{port}')
DB_URI = os.getenv('DB_URI', 'postgresql://wazo-call-logd:Secr7t@127.0.0.1:{port}')


def parse_fields(line: str):
    return [field.strip() for field in line.split('|')]


def parse_raw_cels(text_table: str):
    cels = []
    lines = [
        line
        for line in text_table.strip().split('\n')
        if line and set(line.strip()) != set('+-')
    ]
    logger.debug("parsing %d lines of cel table", len(lines))
    columns = parse_fields(lines.pop(0))
    logger.debug("parsed %d fields in cel table header", len(columns))

    for i, line in enumerate(lines):
        cel = parse_fields(line)
        logger.debug("parsed %d fields in row %d", len(cel), i)
        assert len(cel) == len(columns), (columns, cel)
        cels.append(dict(zip(columns, cel)))
    return cels


def raw_cels(cel_output, row_count=None):
    '''
    this decorator takes the output of a psql query
    and parses it into CEL entries that are loaded into the database
    '''
    cels = parse_raw_cels(cel_output)
    if row_count:
        assert (
            len(cels) == row_count
        ), f"parsed row count ({len(cels)}) different from expected row count ({row_count})"

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
    caller = caller or ALICE
    callee = callee or BOB
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
        raise Exception(f'Could not create client {self.name}')


class _BaseIntegrationTest(AssetLaunchingTestCase):
    bus: CallLogBusClient
    call_logd: CallLogdClient
    database: DbHelper
    cel_database: DbHelper
    filesystem: FileSystemClient
    email: EmailClient
    auth: AuthClient

    assets_root = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reset_clients()
        cls.wait_strategy.wait(cls)

    @classmethod
    def reset_clients(cls):
        cls.bus = cls.make_bus()
        cls.call_logd = cls.make_call_logd()
        cls.database = cls.make_database()
        cls.cel_database = cls.make_cel_database()
        cls.filesystem = cls.make_filesystem()
        cls.email = cls.make_email()
        cls.auth = cls.make_auth()
        if not isinstance(cls.auth, WrongClient):
            until.true(cls.auth.is_up, tries=5)
            cls.configure_wazo_auth_for_multitenants()

    @classmethod
    def make_call_logd(cls):
        try:
            port = cls.service_port(9298, 'call-logd')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='call-logd')

        return CallLogdClient(
            '127.0.0.1',
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

        return AuthClient('127.0.0.1', port)

    @classmethod
    def make_database(cls):
        try:
            port = cls.service_port(5432, 'postgres')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='database')

        return DbHelper.build(
            'wazo-call-logd',
            'Secr7t',
            '127.0.0.1',
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
            '127.0.0.1',
            port,
            'asterisk',
        )

    @classmethod
    def make_bus(cls):
        try:
            port = cls.service_port(5672, 'rabbitmq')
        except (NoSuchService, NoSuchPort):
            return WrongClient(name='bus')
        bus = CallLogBusClient.from_connection_fields(
            port=port, exchange_name='wazo-headers', exchange_type='headers'
        )
        return bus

    @classmethod
    def make_confd(cls):
        return ConfdClient('127.0.0.1', cls.service_port(9486, 'confd'))

    @classmethod
    def make_filesystem(cls):
        return FileSystemClient(execute=cls.docker_exec)

    @classmethod
    def make_email(cls):
        return EmailClient('smtp', execute=cls.docker_exec)

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
                {"tenant_uuid": str(MASTER_TENANT), "uuid": str(MASTER_USER_UUID)},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                USER_1_TOKEN,
                USER_1_UUID,
                WAZO_UUID,
                {"tenant_uuid": str(USERS_TENANT), "uuid": str(USER_1_UUID)},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                USER_2_TOKEN,
                USER_2_UUID,
                WAZO_UUID,
                {"tenant_uuid": str(USERS_TENANT), "uuid": str(USER_2_UUID)},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                OTHER_USER_TOKEN,
                OTHER_USER_UUID,
                WAZO_UUID,
                {"tenant_uuid": str(OTHER_TENANT), "uuid": str(OTHER_USER_UUID)},
            )
        )
        cls.auth.set_valid_credentials(
            MockCredentials(EXPORT_SERVICE_ID, EXPORT_SERVICE_KEY),
            MASTER_TOKEN,
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

    @contextmanager
    def set_token(self, token):
        old_token = self.call_logd._token_id
        self.call_logd.set_token(token)
        yield
        self.call_logd.set_token(old_token)

    def _get_tomorrow(self, timezone=None):
        timezone = timezone or pytz.utc
        today = datetime.now(pytz.utc).astimezone(timezone)
        return timezone.normalize(
            timezone.localize(datetime(today.year, today.month, today.day))
            + relativedelta(days=1)
        ).isoformat(timespec='seconds')

    @property
    def session(self):
        return self._Session()

    @property
    def cel_session(self):
        return self._CELSession()

    def setUp(self):
        db_uri = DB_URI.format(port=self.service_port(5432, 'postgres'))
        self._Session = new_db_session(db_uri)

        cel_db_uri = CEL_DB_URI.format(port=self.service_port(5432, 'cel-postgres'))
        self._CELSession = new_db_session(cel_db_uri)

        self.dao = DAO(self._Session, self._CELSession)

        tenant_uuids = [MASTER_TENANT, OTHER_TENANT, USERS_TENANT]
        self.dao.tenant.create_all_uuids_if_not_exist(tenant_uuids)

    def tearDown(self):
        self._Session.rollback()
        self._Session.remove()
        self._CELSession.rollback()
        self._CELSession.remove()


class IntegrationTest(_BaseIntegrationTest):
    asset = 'base'
    service = 'call-logd'
    wait_strategy = NoWaitStrategy()

    def setUp(self):
        super().setUp()
        self.call_logd.set_token(MASTER_TOKEN)


class DBIntegrationTest(_BaseIntegrationTest):
    asset = 'database'
    service = 'postgres'
    wait_strategy = NoWaitStrategy()

    def setUp(self):
        super().setUp()
        self.dao.config.find_or_create()


class RawCelIntegrationTest(_BaseIntegrationTest):
    asset = 'base'
    service = 'call-logd'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def setUp(self):
        super().setUp()
        self.call_logd.set_token(MASTER_TOKEN)
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
        with self.database.queries() as queries:
            queries.clear_call_logs()

        yield

        with self.database.queries() as queries:
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
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    logger.debug("call_log=%s", call_log)
                    if call_log:
                        logger.debug("call_log.participants=%s", call_log.participants)
                    assert_that(call_log, expected)

            until.assert_(call_log_generated, tries=5)
