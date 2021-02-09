# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_properties,
)
from wazo_call_logd_client.exceptions import CallLogdError
from xivo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT as MAIN_TENANT,
    MASTER_TOKEN as MAIN_TOKEN,
    OTHER_TENANT as SUB_TENANT,
)
from .helpers.database import call_log


class TestRecording(IntegrationTest):

    asset = 'base'

    @call_log(
        **{'id': 1},
        date='2021-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/foobar.wav'}, {'path': 'tmp/foobar2.wav'}],
    )
    def test_get_media(self):
        cdr_id = 1
        self.filesystem.create_file('/tmp/foobar.wav', content='my-recording-content')
        self.filesystem.create_file('/tmp/foobar2.wav', content='hidden')
        recording = self.call_logd.cdr.get_by_id(cdr_id)['recordings'][0]
        response = self.call_logd.cdr.get_recording_media(cdr_id, recording['uuid'])
        expected_filename = recording['filename']
        assert_that(response.text, equal_to('my-recording-content'))
        assert_that(
            response.headers['Content-Disposition'],
            equal_to(f'attachment; filename={expected_filename}'),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    def test_get_media_with_invalid_cdr(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(2, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='cdr-not-found-with-given-id')
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    @call_log(**{'id': 2}, recordings=[])
    def test_get_media_with_wrong_cdr(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(2, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='recording-not-found')
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': None}])
    def test_get_media_with_recording_deleted(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(1, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='recording-media-not-found')
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/denied.wav'}])
    def test_get_media_when_file_has_wrong_permission(self):
        self.filesystem.create_file('/tmp/denied.wav', mode='000')
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(1, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=500, error_id='recording-media-permission-denied'
                )
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/deleted.wav'}])
    def test_get_media_when_file_deleted_on_filesystem(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(1, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=500, error_id='recording-media-filesystem-not-found'
                )
            ),
        )

    @call_log(
        **{'id': 10},
        tenant_uuid=MAIN_TENANT,
        recordings=[{'path': '/tmp/10-recording.wav'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=SUB_TENANT,
        recordings=[{'path': '/tmp/11-recording.wav'}],
    )
    def test_get_media_mutli_tenant(self):
        self.filesystem.create_file('/tmp/11-recording.wav', content='11-recording')

        rec_uuid = self.call_logd.cdr.get_by_id(10)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(
                10, rec_uuid, tenant_uuid=SUB_TENANT
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='cdr-not-found-with-given-id')
            ),
        )

        rec_uuid = self.call_logd.cdr.get_by_id(11)['recordings'][0]['uuid']
        response = self.call_logd.cdr.get_recording_media(
            11, rec_uuid, tenant_uuid=MAIN_TENANT
        )
        assert_that(response.text, equal_to('11-recording'))

    @call_log(
        **{'id': 1},
        tenant_uuid=MAIN_TENANT,
        recordings=[{'path': '/tmp/foobar.wav'}],
    )
    def test_get_media_using_token_tenant_query_string(self):
        cdr_id = 1
        self.filesystem.create_file('/tmp/foobar.wav', content='my-recording-content')
        recording_uuid = self.call_logd.cdr.get_by_id(cdr_id)['recordings'][0]['uuid']
        port = self.service_port(9298, 'call-logd')
        base_url = f'http://localhost:{port}/1.0'
        api_url = f'{base_url}/cdr/{cdr_id}/recordings/{recording_uuid}/media'

        params = {'tenant': MAIN_TENANT, 'token': MAIN_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.text, equal_to('my-recording-content'))

        params = {'tenant': SUB_TENANT, 'token': MAIN_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.status_code, equal_to(404))
