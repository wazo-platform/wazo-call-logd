# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import ExitStack, contextmanager
from datetime import datetime as dt
from datetime import timedelta as td
import logging
from types import SimpleNamespace
from hamcrest import (
    assert_that,
    contains_exactly,
    has_entries,
    has_item,
    has_properties,
    not_,
)
from wazo_test_helpers import until

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    OTHER_TENANT,
    SERVICE_TENANT,
    USERS_TENANT,
)
from .helpers.database import (
    DbHelper,
    call_log_fixture,
    retention_fixture,
    export_fixture,
)
from .helpers.filesystem import file_fixture
from .helpers.wait_strategy import CallLogdComponentsWaitStrategy


logger = logging.getLogger(__name__)


@contextmanager
def tables_counts(db_helper: DbHelper):
    with db_helper.queries() as queries:
        before_counts = queries.count_all()

    info = SimpleNamespace()
    info.pre_count = before_counts
    try:
        yield info
    finally:
        with db_helper.queries() as queries:
            after_counts = queries.count_all()
        info.post_count = after_counts
        info.diff = {
            name: after_counts.get(name, 0) - before_counts.get(name, 0)
            for name in (after_counts.keys() | before_counts.keys())
        }


class TestTenantDelete(IntegrationTest):
    wait_strategy = CallLogdComponentsWaitStrategy(["bus_consumer", "service_token"])

    def tearDown(self):
        self.resources.close()
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.resources = ExitStack()
        # set up fixtures for USERS_TENANT
        self.resources.enter_context(
            call_log_fixture(
                self.database,
                dict(
                    id=1,
                    date='2023-01-01T01:00:00+01:00',
                    recordings=[{'path': '/tmp/record1.wav'}],
                    tenant_uuid=USERS_TENANT,
                ),
            )
        )
        self.resources.enter_context(
            retention_fixture(self.database, dict(tenant_uuid=USERS_TENANT))
        )
        self.resources.enter_context(
            export_fixture(
                self.database,
                dict(
                    tenant_uuid=USERS_TENANT,
                    requested_at=dt.utcnow() - td(days=2),
                    path='/tmp/export1',
                ),
            )
        )
        self.resources.enter_context(file_fixture(self.filesystem, '/tmp/record1.wav'))
        self.resources.enter_context(file_fixture(self.filesystem, '/tmp/export1'))

        # fixtures for OTHER_TENANT
        self.resources.enter_context(
            call_log_fixture(
                self.database,
                dict(
                    id=2,
                    date='2023-01-01T01:00:00+01:00',
                    recordings=[{'path': '/tmp/record2.wav'}],
                    tenant_uuid=OTHER_TENANT,
                ),
            )
        )

        self.resources.enter_context(
            retention_fixture(self.database, dict(tenant_uuid=OTHER_TENANT))
        )

        self.resources.enter_context(
            export_fixture(
                self.database,
                dict(
                    tenant_uuid=OTHER_TENANT,
                    requested_at=dt.utcnow() - td(days=2),
                    path='/tmp/export2',
                ),
            )
        )
        self.resources.enter_context(file_fixture(self.filesystem, '/tmp/export2'))
        self.resources.enter_context(file_fixture(self.filesystem, '/tmp/record2.wav'))

    @classmethod
    def sync_db(cls):
        cls.docker_exec(['wazo-call-logd-sync-db', '--debug'])

    def _assert_only_other_tenant_resources_remain(self):
        assert_that(self.filesystem.path_exists('/tmp/record2.wav'))
        assert_that(self.filesystem.path_exists('/tmp/export2'))

        with self.database.queries() as queries:
            assert_that(
                queries.find_all_call_log(),
                contains_exactly(has_properties(id=2, tenant_uuid=OTHER_TENANT)),
            )

            assert_that(
                queries.find_retentions(),
                contains_exactly(has_properties(tenant_uuid=OTHER_TENANT)),
            )

            recordings = queries.find_all_recordings()
            assert_that(
                recordings,
                contains_exactly(
                    has_properties(
                        call_log_id=2, call_log=has_properties(tenant_uuid=OTHER_TENANT)
                    )
                ),
            )

            assert_that(
                queries.find_all_exports(),
                contains_exactly(
                    has_properties(tenant_uuid=OTHER_TENANT, path='/tmp/export2')
                ),
            )

    def _assert_users_tenant_resources_deleted(self):
        assert_that(not self.filesystem.path_exists('/tmp/record1.wav'))
        assert_that(not self.filesystem.path_exists('/tmp/export1'))

        with self.database.queries() as queries:
            # USERS_TENANT is no more
            assert_that(
                queries.find_all_tenants(),
                not_(has_item(has_properties(uuid=USERS_TENANT))),
            )

    def test_tenant_deleted_event(self, *resources):
        def tenant_deleted():
            with self.database.queries() as queries:
                tenant = queries.find_tenant(USERS_TENANT)
                assert tenant is None

        with tables_counts(self.database) as info:
            self.bus.send_tenant_deleted(USERS_TENANT)
            until.assert_(tenant_deleted, tries=5, interval=5)

        assert_that(not self.filesystem.path_exists('/tmp/record1.wav'))
        assert_that(not self.filesystem.path_exists('/tmp/export1'))

        assert_that(
            info.diff,
            has_entries(
                call_logd_export=-1,
                call_logd_call_log=-1,
                call_logd_recording=-1,
                call_logd_retention=-1,
                call_logd_tenant=-1,
            ),
        )

        self._assert_users_tenant_resources_deleted()
        self._assert_only_other_tenant_resources_remain()

    def test_tenant_deleted_syncdb(self, *_):
        # remove USERS_TENANT from auth service
        self.auth.set_tenants(
            {
                'uuid': str(MASTER_TENANT),
                'name': 'call-logd-tests-master',
                'parent_uuid': str(MASTER_TENANT),
            },
            {
                'uuid': str(OTHER_TENANT),
                'name': 'call-logd-tests-other',
                'parent_uuid': str(MASTER_TENANT),
            },
            {
                'uuid': str(SERVICE_TENANT),
                'name': 'call-logd-tests-other',
                'parent_uuid': str(MASTER_TENANT),
            },
        )
        with tables_counts(self.database) as info:
            logger.debug("table counts pre-sync: %s", info.pre_count)
            self.sync_db()
        logger.debug("table counts post-sync: %s", info.post_count)
        logger.debug("table counts diff: %s", info.diff)

        assert_that(
            info.diff,
            has_entries(
                call_logd_export=-1,
                call_logd_call_log=-1,
                call_logd_recording=-1,
                call_logd_retention=-1,
                call_logd_tenant=-1,
            ),
        )

        self._assert_users_tenant_resources_deleted()
        self._assert_only_other_tenant_resources_remain()
