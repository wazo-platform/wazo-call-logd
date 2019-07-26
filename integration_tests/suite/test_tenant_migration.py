# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import closing

import requests
from hamcrest import assert_that

from xivo import url_helpers
from xivo_dao.alchemy.call_log import CallLog

from .helpers.base import IntegrationTest
from .helpers.constants import (
    USER_1_UUID,
    USER_2_UUID,
    USERS_TENANT,
    OTHER_USER_UUID,
    OTHER_TENANT,
    MASTER_TOKEN,
    SERVICE_TENANT,
)
from .helpers.database import call_logs

NOT_MIGRATED_TENANT = "00000000-0000-0000-0000-000000000000"


class TestTenantMigration(IntegrationTest):

    asset = 'base'

    @call_logs([
        {'id': 10,
         'tenant_uuid': NOT_MIGRATED_TENANT,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'default',
         'requested_internal_context': 'default',
         'source_internal_context': 'default',
         'destination_internal_context': 'default',
         'participants': [{'user_uuid': USER_1_UUID,
                           'line_id': '1',
                           'role': 'source'}]},
        {'id': 11,
         'tenant_uuid': NOT_MIGRATED_TENANT,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'default',
         'requested_internal_context': 'default',
         'source_internal_context': 'default',
         'destination_internal_context': 'default',
         'participants': [{'user_uuid': USER_2_UUID,
                           'line_id': '1',
                           'role': 'source'}]},
        {'id': 12,
         'tenant_uuid': NOT_MIGRATED_TENANT,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'other',
         'requested_internal_context': 'other',
         'source_internal_context': 'other',
         'destination_internal_context': 'other',
         'participants': [{'user_uuid': OTHER_USER_UUID,
                           'line_id': '1',
                           'role': 'source'}]},
        {'id': 13,
         'tenant_uuid': NOT_MIGRATED_TENANT,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'no-longer-exists',
         'requested_internal_context': 'other',
         'source_internal_context': 'other',
         'destination_internal_context': 'other',
         'participants': [{'user_uuid': OTHER_USER_UUID,
                           'line_id': '1',
                           'role': 'source'}]}

    ])
    def test_tenant_migration(self):
        base = 'https://localhost:{port}/1.0/'.format(
            port=self.service_port(9298, 'call-logd'))
        url = url_helpers.base_join(base, 'tenant-migration')

        payload = {
            'contexts': [
                {'context': 'default', 'tenant_uuid': USERS_TENANT},
                {'context': 'other', 'tenant_uuid': OTHER_TENANT},
            ],
        }
        headers = {'X-Auth-Token': MASTER_TOKEN, 'Content-Type': 'application/json'}
        resp = requests.post(url, json=payload, headers=headers, verify=False)
        resp.raise_for_status()

        with self.database.queries() as queries:
            with closing(queries.Session()) as session:
                query = session.query(CallLog)
                for call_log in query.all():
                    if call_log.requested_context == 'default':
                        assert_that(call_log.tenant_uuid, USERS_TENANT)
                    elif call_log.requested_context == 'other':
                        assert_that(call_log.tenant_uuid, OTHER_TENANT)
                    else:
                        assert_that(call_log.tenant_uuid, SERVICE_TENANT)
