# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid

from datetime import (
    timedelta as td,
    timezone as tz,
)
from hamcrest import (
    assert_that,
    has_properties,
    none,
)

from .helpers.base import DBIntegrationTest
from .helpers.database import export
from .helpers.constants import (
    MASTER_TENANT,
    OTHER_TENANT,
)


class TestDBExport(DBIntegrationTest):
    @export(path='exp1')
    @export(path='exp2', tenant_uuid=OTHER_TENANT)
    def test_get_by_uuid_tenant_filter(self, export1, export2):
        master_tenant = uuid.UUID(MASTER_TENANT)
        other_tenant = uuid.UUID(OTHER_TENANT)
        result = self.dao.export.get_by_uuid(export1['uuid'], [master_tenant])
        assert_that(result, has_properties(uuid=export1['uuid']))

        result = self.dao.export.get_by_uuid(export1['uuid'], [other_tenant])
        assert_that(result, none())

    @export()
    def test_export_filename(self, export):
        export_uuid = export['uuid']
        master_tenant = uuid.UUID(MASTER_TENANT)
        result = self.dao.export.get_by_uuid(export_uuid, [master_tenant])
        offset = export['date'].utcoffset() or td(seconds=0)
        date_utc = (export['date'] - offset).replace(tzinfo=tz.utc)
        export_date_utc = date_utc.strftime('%Y-%m-%dT%H_%M_%SUTC')
        assert_that(result, has_properties(filename=f'{export_date_utc}-{export_uuid}.zip'))

    @export()
    def test_status(self, export):
        export_uuid = export['uuid']
        result = self.dao.export.get_by_uuid(export_uuid)
        assert_that(result, has_properties(status='in_progress'))
        result.done = True
        assert_that(result, has_properties(status='deleted'))
        result.path = 'test-path'
        assert_that(result, has_properties(status='finished'))
