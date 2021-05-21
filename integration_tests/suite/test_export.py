# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytz
import requests

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_entries,
    has_properties,
)

from wazo_call_logd_client.exceptions import CallLogdError
from xivo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    MASTER_TOKEN,
    OTHER_TENANT,
)
from .helpers.database import export


class TestExports(IntegrationTest):
    @export()
    def test_get_in_progress_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=str(export['uuid']),
                tenant_uuid=MASTER_TENANT,
                date=pytz.utc.localize(export['date']).isoformat(),
                status='in_progress',
            ),
        )

    @export(status='finished', path='file-test')
    def test_get_finished_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=str(export['uuid']),
                tenant_uuid=MASTER_TENANT,
                date=pytz.utc.localize(export['date']).isoformat(),
                status='finished',
            ),
        )

    @export(status='deleted', path=None)
    def test_get_deleted_export(self, export):
        result = self.call_logd.export.get(export['uuid'], tenant_uuid=MASTER_TENANT)
        assert_that(
            result,
            has_entries(
                uuid=str(export['uuid']),
                tenant_uuid=MASTER_TENANT,
                date=pytz.utc.localize(export['date']).isoformat(),
                status='deleted',
            ),
        )

    @export()
    def test_get_export_multitenant(self, export):
        assert_that(
            calling(self.call_logd.export.get).with_args(
                export['uuid'], tenant_uuid=OTHER_TENANT
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    # Downloading

    @export(status='in_progress', path=None)
    def test_download_not_finished_export(self, export):
        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=202,
                    error_id='export-not-done-yet',
                )
            ),
        )

    @export(status='finished', path='/tmp/foobar.zip')
    def test_download_finished_export(self, export):
        self.filesystem.create_file('/tmp/foobar.zip', content='zipfile')
        export_from_api = self.call_logd.export.get(export['uuid'])
        assert_that(export_from_api, has_entries(status='finished'))

        result = self.call_logd.export.download(export['uuid'])
        expected_filename = export_from_api['filename']
        assert_that(result.text, equal_to('zipfile'))
        assert_that(
            result.headers['Content-Disposition'],
            equal_to(f'attachment; filename={expected_filename}'),
        )

    @export(status='finished', path='/tmp/foobar2.zip')
    def test_download_finished_export_but_file_deleted_on_filesystem(self, export):
        export_from_api = self.call_logd.export.get(export['uuid'])
        assert_that(export_from_api, has_entries(status='finished'))

        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(status_code=500, error_id='export-filesystem-not-found')
            ),
        )

    @export(status='finished', path='/tmp/foobar3.zip')
    def test_download_finished_export_but_file_has_wrong_permissions(self, export):
        self.filesystem.create_file('/tmp/foobar3.zip', content='zipfile', mode='000')
        export_from_api = self.call_logd.export.get(export['uuid'])
        assert_that(export_from_api, has_entries(status='finished'))

        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(status_code=500, error_id='export-permission-denied')
            ),
        )

    @export(status='finished', path='/tmp/foobar4.zip')
    def test_download_export_with_token_tenant_in_query_string(self, export):
        self.filesystem.create_file('/tmp/foobar4.zip', content='zipfile')

        port = self.service_port(9298, 'call-logd')
        base_url = f'http://127.0.0.1:{port}/1.0'
        api_url = f"{base_url}/exports/{export['uuid']}/download"

        params = {'tenant': MASTER_TENANT, 'token': MASTER_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.text, equal_to('zipfile'))

        params = {'tenant': OTHER_TENANT, 'token': MASTER_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.status_code, equal_to(404))
