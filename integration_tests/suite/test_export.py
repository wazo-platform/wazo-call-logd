# Copyright 2021-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import requests
import zipfile

from datetime import datetime, timedelta
from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_key,
    has_properties,
)
from io import BytesIO

from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT,
    MASTER_TOKEN,
    OTHER_TENANT,
    USER_1_UUID,
    USER_2_UUID,
)
from .helpers.database import call_log, export, recording
from .helpers.wait_strategy import CallLogdEverythingUpWaitStrategy


class TestExportAPI(IntegrationTest):
    @export(
        tenant_uuid=MASTER_TENANT,
        requested_at=datetime.fromisoformat('2021-05-25T15:00:00'),
    )
    def test_get_multitenant(self, export):
        assert_that(
            calling(self.call_logd.export.get).with_args(
                export['uuid'], tenant_uuid=OTHER_TENANT
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )
        result = self.call_logd.export.get(export['uuid'])
        assert_that(
            result,
            has_entries(
                uuid=str(export['uuid']),
                tenant_uuid=MASTER_TENANT,
                status='pending',
                requested_at='2021-05-25T15:00:00+00:00',
            ),
        )

    # Downloading

    @export(status='pending', path=None)
    def test_download_pending(self, export):
        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=202,
                    error_id='export-not-done-yet',
                )
            ),
        )

    @export(status='processing', path=None)
    def test_download_processing(self, export):
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
    def test_download_finished(self, export):
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
        self.filesystem.remove_file('/tmp/foobar.zip')

    @export(status='finished', path='/tmp/foobar2.zip')
    def test_download_finished_when_file_deleted_on_filesystem(self, export):
        export_from_api = self.call_logd.export.get(export['uuid'])
        assert_that(export_from_api, has_entries(status='finished'))

        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(status_code=500, error_id='export-filesystem-not-found')
            ),
        )

    @export(status='finished', path='/tmp/foobar3.zip')
    def test_download_finished_when_file_has_wrong_permissions(self, export):
        self.filesystem.create_file('/tmp/foobar3.zip', content='zipfile', mode='000')
        export_from_api = self.call_logd.export.get(export['uuid'])
        assert_that(export_from_api, has_entries(status='finished'))

        assert_that(
            calling(self.call_logd.export.download).with_args(export['uuid']),
            raises(CallLogdError).matching(
                has_properties(status_code=500, error_id='export-permission-denied')
            ),
        )
        self.filesystem.remove_file('/tmp/foobar3.zip')

    @export(status='finished', path='/tmp/foobar4.zip')
    def test_download_when_token_tenant_in_query_string(self, export):
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

        self.filesystem.remove_file('/tmp/foobar4.zip')


class TestRecordingMediaExport(IntegrationTest):

    asset = 'base'
    wait_strategy = CallLogdEverythingUpWaitStrategy()

    def _recording_filename(self, rec):
        start = rec['start_time'].strftime('%Y-%m-%dT%H_%M_%SUTC')
        return f"{start}-{rec['call_log_id']}-{rec['uuid']}.wav"

    def assert_zip_content(self, zip_bytes, expected):
        zipped_export_bytes = BytesIO(zip_bytes)

        with zipfile.ZipFile(zipped_export_bytes, 'r') as zipped_export:
            files = zipped_export.infolist()
            properties_matchers = []

            for file in expected:
                assert_that(
                    zipped_export.read(file['name']).decode('utf-8'),
                    equal_to(file['content']),
                )
                properties_matchers.append(has_properties(filename=file['name']))

            assert_that(files, contains_inanyorder(*properties_matchers))

    def _export_status_is(self, export_uuid, status):
        export = self.call_logd.export.get(export_uuid)
        assert_that(export['status'], equal_to(status))

    def test_given_wrong_params_then_400(self):
        wrong_params = {'abcd', '12:345', '2017-042-10', '-1'}

        def _assert_400(key, value, python_key=None):
            python_key = python_key or key
            kwargs = {python_key: value}
            assert_that(
                calling(self.call_logd.cdr.export_recording_media).with_args(**kwargs),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key(key))
                ),
            )

        for wrong_param in wrong_params:
            _assert_400('from', wrong_param, python_key='from_')
            _assert_400('until', wrong_param)
            _assert_400('call_direction', wrong_param)
            _assert_400('email', wrong_param)
            _assert_400('from_id', wrong_param)
            _assert_400('recurse', wrong_param)

    @call_log(**{'id': 10})
    @call_log(**{'id': 11})
    @recording(call_log_id=10, path='/tmp/10-recording.wav')
    @recording(call_log_id=11, path='/tmp/11-recording.wav')
    def test_create_when_no_params(self, rec1, rec2):
        self.filesystem.create_file('/tmp/10-recording.wav', content='10-recording')
        self.filesystem.create_file('/tmp/11-recording.wav', content='11-recording')

        export = self.call_logd.cdr.export_recording_media()
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('10', self._recording_filename(rec1)),
                    'content': '10-recording',
                },
                {
                    'name': os.path.join('11', self._recording_filename(rec2)),
                    'content': '11-recording',
                },
            ],
        )
        self.filesystem.remove_file('/tmp/10-recording.wav')
        self.filesystem.remove_file('/tmp/11-recording.wav')

    @call_log(**{'id': 10})
    @call_log(**{'id': 11})
    @recording(call_log_id=10, path='/tmp/10-recording.wav')
    @recording(call_log_id=11, path='/tmp/11-recording.wav')
    def test_create_from_cdr_ids(self, rec1, rec2):
        self.filesystem.create_file('/tmp/10-recording.wav', content='10-recording')
        self.filesystem.create_file('/tmp/11-recording.wav', content='11-recording')

        export = self.call_logd.cdr.export_recording_media(cdr_ids=[10, 11])
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('10', self._recording_filename(rec1)),
                    'content': '10-recording',
                },
                {
                    'name': os.path.join('11', self._recording_filename(rec2)),
                    'content': '11-recording',
                },
            ],
        )
        self.filesystem.remove_file('/tmp/10-recording.wav')
        self.filesystem.remove_file('/tmp/11-recording.wav')

    @call_log(**{'id': 10})
    def test_create_from_cdr_ids_when_no_recording(self):
        assert_that(
            calling(self.call_logd.cdr.export_recording_media).with_args(cdr_ids=[10]),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='no-recording-to-export')
            ),
        )

    @call_log(**{'id': 10})
    @recording(
        call_log_id=10,
        path='/tmp/10-recording.wav',
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
    )
    def test_create_from_cdr_ids_when_recording_file_permissions_are_wrong(self, rec1):
        self.filesystem.create_file(
            '/tmp/10-recording.wav', content='10-recording', mode='000'
        )

        export_uuid = self.call_logd.cdr.export_recording_media(cdr_ids=[10])['uuid']

        until.assert_(self._export_status_is, export_uuid, 'error', timeout=5)
        result = self.call_logd.export.get(export_uuid)
        assert_that(result, has_entries(status='error'))
        self.filesystem.remove_file('/tmp/10-recording.wav')

    @call_log(**{'id': 10})
    @recording(call_log_id=10, path='/tmp/10-recording.wav')
    def test_create_from_cdr_ids_when_recording_file_does_not_exist(self, rec1):
        export_uuid = self.call_logd.cdr.export_recording_media(cdr_ids=[10])['uuid']

        until.assert_(self._export_status_is, export_uuid, 'error', timeout=5)
        result = self.call_logd.export.get(export_uuid)
        assert_that(result, has_entries(status='error'))

    @call_log(**{'id': 10})
    @recording(call_log_id=10, path='/tmp/10-recording.wav')
    def test_create_from_cdr_ids_when_previous_export_failure(self, rec1):
        export_uuid = self.call_logd.cdr.export_recording_media(cdr_ids=[10])['uuid']

        until.assert_(self._export_status_is, export_uuid, 'error', timeout=5)

        self.filesystem.create_file('/tmp/10-recording.wav', content='10-recording')
        export_uuid = self.call_logd.cdr.export_recording_media(cdr_ids=[10])['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)
        self.filesystem.remove_file('/tmp/10-recording.wav')

    @call_log(**{'id': 1}, date='2021-05-20T15:00:00')
    @call_log(**{'id': 2}, date='2021-05-21T15:00:00')
    @call_log(**{'id': 3}, date='2021-05-22T15:00:00')
    @call_log(**{'id': 4}, date='2021-05-23T15:00:00')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    @recording(call_log_id=4, path='/tmp/4-recording.wav')
    def test_create_from_time_range(self, rec1, rec2, _):
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')
        self.filesystem.create_file('/tmp/4-recording.wav', content='4-recording')
        export = self.call_logd.cdr.export_recording_media(
            from_='2021-05-20T00:00:00',
            until='2021-05-23T00:00:00',
        )
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec1)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec2)),
                    'content': '3-recording',
                },
            ],
        )
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')
        self.filesystem.remove_file('/tmp/4-recording.wav')

    @call_log(**{'id': 1}, date='2021-05-20T15:00:00')
    @call_log(**{'id': 2}, date='2021-05-21T15:00:00')
    @call_log(**{'id': 3}, date='2021-05-22T15:00:00')
    @call_log(**{'id': 4}, date='2021-05-23T15:00:00')
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_using_from_id_param(self, _, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export_uuid = self.call_logd.cdr.export_recording_media(from_id=2)['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)

        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )
        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(**{'id': 1}, date='2021-05-20T15:00:00', direction='inbound')
    @call_log(**{'id': 2}, date='2021-05-21T15:00:00', direction='internal')
    @call_log(**{'id': 3}, date='2021-05-22T15:00:00', direction='internal')
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_from_call_direction_param(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(call_direction='inbound')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                }
            ],
        )

        export = self.call_logd.cdr.export_recording_media(call_direction='internal')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        assert_that(
            calling(self.call_logd.cdr.export_recording_media).with_args(
                call_direction='outbound'
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='no-recording-to-export')
            ),
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-20T15:00:00',
        participants=[
            {'user_uuid': USER_1_UUID},
        ],
    )
    @call_log(
        **{'id': 2},
        date='2021-05-21T15:00:00',
        participants=[
            {'user_uuid': USER_1_UUID},
            {'user_uuid': USER_2_UUID},
        ],
    )
    @call_log(
        **{'id': 3},
        date='2021-05-22T15:00:00',
        participants=[
            {'user_uuid': USER_2_UUID},
        ],
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_from_user_uuid(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(user_uuid=USER_1_UUID)
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(user_uuid=USER_2_UUID)
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-20T15:00:00',
        participants=[
            {'user_uuid': USER_1_UUID, 'tags': ['chicoutimi']},
        ],
    )
    @call_log(
        **{'id': 2},
        date='2021-05-21T15:00:00',
        participants=[
            {'user_uuid': USER_1_UUID, 'tags': ['chicoutimi', 'quebec']},
        ],
    )
    @call_log(
        **{'id': 3},
        date='2021-05-22T15:00:00',
        participants=[
            {'user_uuid': USER_1_UUID, 'tags': ['quebec']},
        ],
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_from_tags(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(tags='chicoutimi')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(tags='quebec')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(tags='chicoutimi,quebec')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                }
            ],
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-20T15:00:00',
        source_name='chicoutimi',
    )
    @call_log(
        **{'id': 2},
        date='2021-05-21T15:00:00',
        source_name='chicoutimi',
        destination_name='quebec',
    )
    @call_log(
        **{'id': 3},
        date='2021-05-22T15:00:00',
        destination_name='quebec',
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_from_search(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(search='chicoutimi')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(search='quebec')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-20T15:00:00',
        source_exten='12345',
    )
    @call_log(
        **{'id': 2},
        date='2021-05-21T15:00:00',
        source_exten='123',
    )
    @call_log(
        **{'id': 3},
        date='2021-05-22T15:00:00',
        destination_exten='45',
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_from_number(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(number='_45')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(number='45')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(number='_23_')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(number='4_')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        assert_that(
            calling(self.call_logd.cdr.export_recording_media).with_args(number='0123'),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='no-recording-to-export')
            ),
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-20T15:00:00',
    )
    @call_log(
        **{'id': 2},
        date='2021-05-21T15:00:00',
        tenant_uuid=OTHER_TENANT,
    )
    @call_log(
        **{'id': 3},
        date='2021-05-22T15:00:00',
        tenant_uuid=OTHER_TENANT,
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    @recording(call_log_id=2, path='/tmp/2-recording.wav')
    @recording(call_log_id=3, path='/tmp/3-recording.wav')
    def test_create_when_recurse(self, rec1, rec2, rec3):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        self.filesystem.create_file('/tmp/2-recording.wav', content='2-recording')
        self.filesystem.create_file('/tmp/3-recording.wav', content='3-recording')

        export = self.call_logd.cdr.export_recording_media(recurse=False)
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
            ],
        )

        export = self.call_logd.cdr.export_recording_media(recurse=True)
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        export_zip = self.call_logd.export.download(export_uuid)
        self.assert_zip_content(
            export_zip.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(rec1)),
                    'content': '1-recording',
                },
                {
                    'name': os.path.join('2', self._recording_filename(rec2)),
                    'content': '2-recording',
                },
                {
                    'name': os.path.join('3', self._recording_filename(rec3)),
                    'content': '3-recording',
                },
            ],
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
        self.filesystem.remove_file('/tmp/2-recording.wav')
        self.filesystem.remove_file('/tmp/3-recording.wav')

    @call_log(
        **{'id': 1},
        date='2021-05-22T15:00:00',
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    def test_events_when_success(self, rec1):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')
        routing_key_created = 'call_logd.export.created'
        routing_key_updated = 'call_logd.export.updated'
        event_created_accumulator = self.bus.accumulator(routing_key_created)
        event_updated_accumulator = self.bus.accumulator(routing_key_updated)
        export_uuid = self.call_logd.cdr.export_recording_media(recurse=False)['uuid']

        def events_received():
            events_created = event_created_accumulator.accumulate()
            events_updated = event_updated_accumulator.accumulate()
            assert_that(
                events_created,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='pending'),
                        required_acl=f'events.{routing_key_created}',
                    ),
                ),
            )
            assert_that(
                events_updated,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='processing'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='finished'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                ),
            )

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)
        until.assert_(events_received, timeout=5)

    @call_log(
        **{'id': 1},
        date='2021-05-22T15:00:00',
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    def test_events_when_file_does_not_exist(self, rec1):
        routing_key_created = 'call_logd.export.created'
        routing_key_updated = 'call_logd.export.updated'
        event_created_accumulator = self.bus.accumulator(routing_key_created)
        event_updated_accumulator = self.bus.accumulator(routing_key_updated)
        export_uuid = self.call_logd.cdr.export_recording_media(recurse=False)['uuid']

        def events_received():
            events_created = event_created_accumulator.accumulate()
            events_updated = event_updated_accumulator.accumulate()
            assert_that(
                events_created,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='pending'),
                        required_acl=f'events.{routing_key_created}',
                    ),
                ),
            )
            assert_that(
                events_updated,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='processing'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='error'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                ),
            )

        until.assert_(self._export_status_is, export_uuid, 'error', timeout=5)
        until.assert_(events_received, timeout=5)

    @call_log(
        **{'id': 1},
        date='2021-05-22T15:00:00',
    )
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    def test_events_when_permission_error(self, rec1):
        self.filesystem.create_file(
            '/tmp/1-recording.wav', content='1-recording', mode='000'
        )
        routing_key_created = 'call_logd.export.created'
        routing_key_updated = 'call_logd.export.updated'
        event_created_accumulator = self.bus.accumulator(routing_key_created)
        event_updated_accumulator = self.bus.accumulator(routing_key_updated)
        export_uuid = self.call_logd.cdr.export_recording_media(recurse=False)['uuid']

        def events_received():
            events_created = event_created_accumulator.accumulate()
            events_updated = event_updated_accumulator.accumulate()
            assert_that(
                events_created,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='pending'),
                        required_acl=f'events.{routing_key_created}',
                    ),
                ),
            )
            assert_that(
                events_updated,
                contains(
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='processing'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                    has_entries(
                        data=has_entries(uuid=export_uuid, status='error'),
                        required_acl=f'events.{routing_key_updated}',
                    ),
                ),
            )

        until.assert_(self._export_status_is, export_uuid, 'error', timeout=5)
        until.assert_(events_received, timeout=5)

    @call_log(**{'id': 1})
    @recording(call_log_id=1, path='/tmp/1-recording.wav')
    def test_email_workflow(self, recording):
        self.filesystem.create_file('/tmp/1-recording.wav', content='1-recording')

        export = self.call_logd.cdr.export_recording_media(email='test@example.com')
        export_uuid = export['uuid']

        until.assert_(self._export_status_is, export_uuid, 'finished', timeout=5)

        url = until.true(self.email.get_last_email_url, timeout=5)

        url = url.replace('https://', 'http://')
        result = requests.get(url)
        self.assert_zip_content(
            result.content,
            [
                {
                    'name': os.path.join('1', self._recording_filename(recording)),
                    'content': '1-recording',
                },
            ],
        )

        self.filesystem.remove_file('/tmp/1-recording.wav')
