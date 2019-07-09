# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import closing

import requests
from hamcrest import assert_that

from xivo import url_helpers
from xivo_dao.alchemy.call_log import CallLog
from xivo_dao.alchemy.call_log_participant import CallLogParticipant

from .helpers.base import IntegrationTest
from .helpers.constants import (
    USER_1_UUID,
    USER_2_UUID,
    USERS_TENANT,
    OTHER_USER_UUID,
    OTHER_TENANT,
    MASTER_TOKEN,
)
from .helpers.database import call_logs

NOT_MIGRATED_TENANT = "00000000-0000-0000-0000-000000000000"


class TestTenantMigration(IntegrationTest):

    asset = 'base'

    @call_logs([
        {'id': 10,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'default',
         'requested_tenant_uuid': NOT_MIGRATED_TENANT,
         'requested_internal_context': 'default',
         'requested_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'source_internal_context': 'default',
         'source_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'destination_internal_context': 'default',
         'destination_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'participants': [{'user_uuid': USER_1_UUID,
                           'tenant_uuid': NOT_MIGRATED_TENANT,
                           'line_id': '1',
                           'role': 'source'}]},
        {'id': 11,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'default',
         'requested_tenant_uuid': NOT_MIGRATED_TENANT,
         'requested_internal_context': 'default',
         'requested_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'source_internal_context': 'default',
         'source_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'destination_internal_context': 'default',
         'destination_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'participants': [{'user_uuid': USER_2_UUID,
                           'tenant_uuid': NOT_MIGRATED_TENANT,
                           'line_id': '1',
                           'role': 'source'}]},
        {'id': 12,
         'date': '2017-03-23 00:00:00',
         'requested_context': 'other',
         'requested_tenant_uuid': NOT_MIGRATED_TENANT,
         'requested_internal_context': 'other',
         'requested_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'source_internal_context': 'other',
         'source_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'destination_internal_context': 'other',
         'destination_internal_tenant_uuid': NOT_MIGRATED_TENANT,
         'participants': [{'user_uuid': OTHER_USER_UUID,
                           'tenant_uuid': NOT_MIGRATED_TENANT,
                           'line_id': '1',
                           'role': 'source'}]}
    ])
    def test_tenant_migration(self):
        base = 'https://localhost:{port}/1.0/'.format(
            port=self.service_port(9298, 'call-logd'))
        url = url_helpers.base_join(base, 'tenant-migration')

        payload = {
            'users': [
                {'user_uuid': USER_1_UUID, 'tenant_uuid': USERS_TENANT},
                {'user_uuid': USER_2_UUID, 'tenant_uuid': USERS_TENANT},
                {'user_uuid': OTHER_USER_UUID, 'tenant_uuid': OTHER_TENANT}
            ],
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
                query = session.query(CallLogParticipant)
                for clp in query.all():
                    if clp.user_uuid in [USER_1_UUID, USER_2_UUID]:
                        assert_that(clp.tenant_uuid, USERS_TENANT)
                    else:
                        assert_that(clp.tenant_uuid, OTHER_TENANT)

                query = session.query(CallLog)
                for cl in query.all():
                    for prefix in ('requested', 'requested_internal',
                                   'source_internal', 'destination_internal'):
                        context = getattr(cl, '{}_context'.format(prefix))
                        tenant_uuid = getattr(
                            cl, '{}_tenant_uuid'.format(prefix)
                        )
                        if context == 'default':
                            assert_that(tenant_uuid, USERS_TENANT)
                        else:
                            assert_that(tenant_uuid, OTHER_TENANT)
