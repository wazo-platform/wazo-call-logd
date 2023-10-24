# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime as dt
from datetime import timedelta as td
from hamcrest import assert_that
from sqlalchemy.sql import text
from wazo_test_helpers import until

from .helpers.base import IntegrationTest
from .helpers.constants import USERS_TENANT
from .helpers.database import retention, call_log, recording, export
from .helpers.filesystem import file_
from .helpers.wait_strategy import CallLogdComponentsWaitStrategy


class TestTenant(IntegrationTest):
    wait_strategy = CallLogdComponentsWaitStrategy(["bus_consumer"])

    def setUp(self):
        self.excluded_tables = []
        self.before_tables_rows_counts = self.count_tables_rows()
        super().setUp()

    def set_tenants(self):
        self.dao.tenant.create_all_uuids_if_not_exist([USERS_TENANT])

    @classmethod
    def sync_db(cls):
        cls.docker_exec(['wazo-call-logd-sync-db', '--debug'])

    def count_tables_rows(self):
        tables_counts = {}
        with self.database.queries() as queries:
            query = text(
                "SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';"
            )
            result = queries.connection.execute(query)
            for row in result:
                if row.tablename not in self.excluded_tables:
                    query = text(f"SELECT COUNT(*) FROM {row.tablename};")
                    count = queries.connection.execute(query).scalar()
                    tables_counts[row.tablename] = count
        return tables_counts

    def diff(self, after_tables_rows_counts):
        diff = {
            k: {
                'before': self.before_tables_rows_counts[k],
                'after': after_tables_rows_counts[k],
            }
            for k in self.before_tables_rows_counts
            if k in after_tables_rows_counts
            and self.before_tables_rows_counts[k] != after_tables_rows_counts[k]
        }
        return diff

    @retention(tenant_uuid=USERS_TENANT)
    @call_log(
        **{'id': 1},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record1.wav'}],
        tenant_uuid=USERS_TENANT,
    )
    @recording(call_log_id=1, path='/tmp/record1.wav')
    @file_('/tmp/record1.wav')
    @export(
        tenant_uuid=USERS_TENANT,
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export1',
    )
    @file_('/tmp/export1')
    def test_tenant_deleted_event(self, *_):
        self.bus.send_tenant_deleted(USERS_TENANT)

        def resources_deleted():
            after_deletion_tables_rows_counts = self.count_tables_rows()
            diff = self.diff(after_deletion_tables_rows_counts)
            assert (
                len(diff) == 0
            ), f'Some tables are not properly cleaned after tenant deletion: {diff}'

        until.assert_(resources_deleted, tries=5, interval=5)

        assert_that(not self.filesystem.path_exists('/tmp/record1.wav'))
        assert_that(not self.filesystem.path_exists('/tmp/export1'))

    @retention(tenant_uuid=USERS_TENANT)
    @call_log(
        **{'id': 1},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record1.wav'}],
        tenant_uuid=USERS_TENANT,
    )
    @recording(call_log_id=1, path='/tmp/record1.wav')
    @file_('/tmp/record1.wav')
    @export(
        tenant_uuid=USERS_TENANT,
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export1',
    )
    @file_('/tmp/export1')
    def test_tenant_deleted_syncdb(self, *_):
        self.sync_db()

        def resources_deleted():
            after_deletion_tables_rows_counts = self.count_tables_rows()
            diff = self.diff(after_deletion_tables_rows_counts)
            assert (
                len(diff) == 0
            ), f'Some tables are not properly cleaned after tenant deletion: {diff}'

        until.assert_(resources_deleted, tries=5, interval=5)

        assert_that(not self.filesystem.path_exists('/tmp/record1.wav'))
        assert_that(not self.filesystem.path_exists('/tmp/export1'))
