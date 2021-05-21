# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests
import zipfile

from datetime import datetime, timedelta
from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_entries,
    has_items,
    has_properties,
)
from io import BytesIO

from wazo_call_logd_client.exceptions import CallLogdError
from xivo_test_helpers import until
from xivo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    MASTER_TOKEN,
    OTHER_TENANT,
)
from .helpers.database import call_log, export, recording


class TestExportAPI(IntegrationTest):
    @export(tenant_uuid=MASTER_TENANT)
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


class TestRecordingMediaExport(IntegrationTest):

    asset = 'base'

    def _recording_filename(self, rec):
        start = rec['start_time'].strftime('%Y-%m-%dT%H_%M_%SUTC')
        return f"{start}-{rec['call_log_id']}-{rec['uuid']}.wav"

    @call_log(**{'id': 10}, tenant_uuid=MASTER_TENANT)
    @call_log(**{'id': 11}, tenant_uuid=OTHER_TENANT)
    @recording(
        call_log_id=10,
        path='/tmp/10-recording.wav',
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
    )
    @recording(
        call_log_id=11,
        path='/tmp/11-recording.wav',
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
    )
    def test_create_export_from_cdr_ids(self, rec1, rec2):
        self.filesystem.create_file('/tmp/10-recording.wav', content='10-recording')
        self.filesystem.create_file('/tmp/11-recording.wav', content='11-recording')

        export_uuid = self.call_logd.cdr.export_recording_media(cdr_ids=[10, 11])['uuid']

        def export_is_finished():
            status = self.call_logd.export.get(export_uuid)['status']
            assert_that(status, equal_to('finished'))

        until.assert_(export_is_finished, timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        zipped_export_bytes = BytesIO(export_zip.content)

        with zipfile.ZipFile(zipped_export_bytes, 'r') as zipped_export:
            files = zipped_export.infolist()
            assert_that(
                files,
                has_items(
                    has_properties(filename=f'10/{self._recording_filename(rec1)}'),
                    has_properties(filename=f'11/{self._recording_filename(rec2)}'),
                )
            )
