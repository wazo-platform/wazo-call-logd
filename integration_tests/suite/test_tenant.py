# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
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
from .helpers.database import DbHelper, retention, call_log, export
from .helpers.filesystem import file_
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


class TestTenant(IntegrationTest):
    wait_strategy = CallLogdComponentsWaitStrategy(["bus_consumer", "service_token"])

    def setUp(self):
        super().setUp()

    @classmethod
    def sync_db(cls):
        cls.docker_exec(['wazo-call-logd-sync-db', '--debug'])

    @retention(tenant_uuid=USERS_TENANT)
    @call_log(
        **{'id': 1},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record1.wav'}],
        tenant_uuid=USERS_TENANT,
    )
    @file_('/tmp/record1.wav')
    @export(
        tenant_uuid=USERS_TENANT,
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export1',
    )
    @file_('/tmp/export1')
    @retention(tenant_uuid=OTHER_TENANT)
    @call_log(
        **{'id': 2},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record2.wav'}],
        tenant_uuid=OTHER_TENANT,
    )
    @file_('/tmp/record2.wav')
    @export(
        tenant_uuid=OTHER_TENANT,
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export2',
    )
    @file_('/tmp/export2')
    def test_tenant_deleted_event(self, *_):
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

        with self.database.queries() as queries:
            # OTHER_TENANT data remain
            assert_that(
                queries.find_all_call_log(),
                contains_exactly(has_properties(id=2, tenant_uuid=OTHER_TENANT)),
            )

            assert_that(
                queries.find_retentions(OTHER_TENANT),
                contains_exactly(has_properties(tenant_uuid=OTHER_TENANT)),
            )

            recordings = queries.find_all_recordings(call_log_id=2)
            assert_that(
                recordings,
                contains_exactly(has_properties(call_log_id=2)),
            )

            assert_that(
                queries.find_all_exports(),
                contains_exactly(has_properties(tenant_uuid=OTHER_TENANT)),
            )

    @retention(tenant_uuid=USERS_TENANT)
    @call_log(
        **{'id': 1},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record1.wav'}],
        tenant_uuid=USERS_TENANT,
    )
    @file_('/tmp/record1.wav')
    @export(
        tenant_uuid=USERS_TENANT,
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export1',
    )
    @file_('/tmp/export1')
    @retention(tenant_uuid=str(OTHER_TENANT))
    @call_log(
        **{'id': 2},
        date='2023-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/record2.wav'}],
        tenant_uuid=str(OTHER_TENANT),
    )
    @export(
        tenant_uuid=str(OTHER_TENANT),
        requested_at=dt.utcnow() - td(days=2),
        path='/tmp/export2',
    )
    @file_('/tmp/record2.wav')
    @file_('/tmp/export2')
    def test_tenant_deleted_syncdb(self, *_):
        # remove USERS_TENANT_TYPED from auth service
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

        assert_that(not self.filesystem.path_exists('/tmp/record1.wav'))
        assert_that(not self.filesystem.path_exists('/tmp/export1'))

        with self.database.queries() as queries:
            # USERS_TENANT is no more
            assert_that(
                queries.find_all_tenants(),
                not_(has_item(has_properties(uuid=USERS_TENANT))),
            )

            # other tenants data remain
            assert_that(
                queries.find_all_call_log(),
                contains_exactly(has_properties(id=2, tenant_uuid=OTHER_TENANT)),
            )

            assert_that(
                queries.find_retentions(OTHER_TENANT),
                contains_exactly(has_properties(tenant_uuid=OTHER_TENANT)),
            )

            recordings = queries.find_all_recordings(call_log_id=2)
            assert_that(
                recordings,
                contains_exactly(has_properties(call_log_id=2)),
            )

            assert_that(
                queries.find_all_exports(),
                contains_exactly(has_properties(tenant_uuid=OTHER_TENANT)),
            )

            assert_that(self.filesystem.path_exists('/tmp/record2.wav'))
            assert_that(self.filesystem.path_exists('/tmp/export2'))
