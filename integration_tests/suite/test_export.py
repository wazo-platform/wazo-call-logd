# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_entries,
)

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    UNKNOWN_UUID,
)
from .helpers.database import export


class TestExports(IntegrationTest):
    @export()
    def test_get_in_progress_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=export['uuid'],
                tenant_uuid=MASTER_TENANT,
                date=export['date'].isoformat(),
                status='in_progress',
            ),
        )

    @export(done=True, path='file-test')
    def test_get_finished_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=export['uuid'],
                tenant_uuid=MASTER_TENANT,
                date=export['date'].isoformat(),
                status='finished',
            ),
        )

    @export(done=True, path=None)
    def test_get_deleted_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=export['uuid'],
                tenant_uuid=MASTER_TENANT,
                date=export['date'].isoformat(),
                status='deleted',
            ),
        )

    @export()
    def test_get_not_finished_export_download(self, export):
        pass

    def test_get_unknown_export(self):
        self.call_logd.export.get(UNKNOWN_UUID)
