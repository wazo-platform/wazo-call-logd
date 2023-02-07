# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_entries,
    has_item,
    has_items,
    has_properties,
)
from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TENANT as MAIN_TENANT,
    MASTER_TOKEN as MAIN_TOKEN,
    OTHER_TENANT as SUB_TENANT,
)
from .helpers.database import call_log
from .helpers.filesystem import file_


class TestRecording(IntegrationTest):
    asset = 'base'

    @call_log(
        **{'id': 1},
        date='2021-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/foobar.wav'}, {'path': '/tmp/foobar2.wav'}],
    )
    @file_('/tmp/foobar.wav', content='my-recording-content')
    @file_('/tmp/foobar2.wav', content='hidden')
    def test_get_media(self):
        cdr_id = 1
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

    @file_('/tmp/denied.wav', mode='000')
    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/denied.wav'}])
    def test_get_media_when_file_has_wrong_permission(self):
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
    @file_('/tmp/11-recording.wav', content='11-recording')
    def test_get_media_mutli_tenant(self):
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
    @file_('/tmp/foobar.wav', content='my-recording-content')
    def test_get_media_using_token_tenant_query_string(self):
        cdr_id = 1
        recording_uuid = self.call_logd.cdr.get_by_id(cdr_id)['recordings'][0]['uuid']
        port = self.service_port(9298, 'call-logd')
        base_url = f'http://127.0.0.1:{port}/1.0'
        api_url = f'{base_url}/cdr/{cdr_id}/recordings/{recording_uuid}/media'

        params = {'tenant': MAIN_TENANT, 'token': MAIN_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.text, equal_to('my-recording-content'))

        params = {'tenant': SUB_TENANT, 'token': MAIN_TOKEN}
        response = requests.get(api_url, params=params)
        assert_that(response.status_code, equal_to(404))

    # Deleting

    @call_log(
        **{'id': 1},
        date='2021-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/foobar.wav'}, {'path': '/tmp/foobar2.wav'}],
    )
    @file_('/tmp/foobar.wav', content='deleted')
    @file_('/tmp/foobar2.wav', content='visible')
    def test_delete_media(self):
        cdr_id = 1
        recording1 = self.call_logd.cdr.get_by_id(cdr_id)['recordings'][0]
        recording2 = self.call_logd.cdr.get_by_id(cdr_id)['recordings'][1]

        self.call_logd.cdr.delete_recording_media(cdr_id, recording1['uuid'])

        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(
                cdr_id, recording1['uuid']
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='recording-media-not-found')
            ),
        )
        recordings = self.call_logd.cdr.get_by_id(cdr_id)['recordings']
        assert_that(
            recordings, has_item(has_entries(uuid=recording1['uuid'], deleted=True))
        )

        response = self.call_logd.cdr.get_recording_media(cdr_id, recording2['uuid'])
        expected_filename = recording2['filename']
        assert_that(response.text, equal_to('visible'))
        assert_that(
            response.headers['Content-Disposition'],
            equal_to(f'attachment; filename={expected_filename}'),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    def test_delete_media_with_invalid_cdr(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.delete_recording_media).with_args(2, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='cdr-not-found-with-given-id')
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    @call_log(**{'id': 2}, recordings=[])
    def test_delete_media_with_wrong_cdr(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.delete_recording_media).with_args(2, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='recording-not-found')
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': None}])
    def test_delete_media_with_recording_already_deleted(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        self.call_logd.cdr.delete_recording_media(1, rec_uuid)
        recording = self.call_logd.cdr.get_by_id(1)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/denied.wav'}])
    @file_('/tmp/denied.wav', mode='000', root=True)
    def test_delete_media_when_file_has_wrong_permission(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.delete_recording_media).with_args(1, rec_uuid),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=500, error_id='recording-media-permission-denied'
                )
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/deleted.wav'}])
    def test_delete_media_when_file_deleted_on_filesystem(self):
        rec_uuid = self.call_logd.cdr.get_by_id(1)['recordings'][0]['uuid']
        self.call_logd.cdr.delete_recording_media(1, rec_uuid)
        recording = self.call_logd.cdr.get_by_id(1)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))

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
    @file_('/tmp/11-recording.wav', content='11-recording')
    def test_delete_media_mutli_tenant(self):
        rec_uuid = self.call_logd.cdr.get_by_id(10)['recordings'][0]['uuid']
        assert_that(
            calling(self.call_logd.cdr.delete_recording_media).with_args(
                10, rec_uuid, tenant_uuid=SUB_TENANT
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=404, error_id='cdr-not-found-with-given-id')
            ),
        )

        rec_uuid = self.call_logd.cdr.get_by_id(11)['recordings'][0]['uuid']
        self.call_logd.cdr.delete_recording_media(11, rec_uuid, tenant_uuid=MAIN_TENANT)
        response = self.call_logd.cdr.get_by_id(11)['recordings'][0]
        assert_that(response, has_entries(uuid=rec_uuid, deleted=True))

    # Deleting recording media from multiple CDRs

    def test_delete_media_multi_cdr_no_body(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args(None),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='invalid-data')
            ),
        )

    def test_delete_media_multi_cdr_no_cdr(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args([]),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='invalid-data')
            ),
        )

    @call_log(
        **{'id': 1},
        date='2021-01-01T01:00:00+01:00',
        recordings=[{'path': '/tmp/foobar.wav'}, {'path': '/tmp/foobar2.wav'}],
    )
    @call_log(
        **{'id': 2},
        date='2021-01-01T03:00:00+01:00',
        recordings=[{'path': '/tmp/foobar3.wav'}],
    )
    @call_log(
        **{'id': 3},
        date='2021-01-01T03:00:00+01:00',
        recordings=[{'path': '/tmp/foobar4.wav'}],
    )
    @file_('/tmp/foobar.wav', content='deleted')
    @file_('/tmp/foobar2.wav', content='deleted')
    @file_('/tmp/foobar3.wav', content='deleted')
    @file_('/tmp/foobar4.wav', content='visible')
    def test_delete_media_multi_cdr(self):
        cdr_ids = [1, 2, 3]
        recording1 = self.call_logd.cdr.get_by_id(cdr_ids[0])['recordings'][0]
        recording2 = self.call_logd.cdr.get_by_id(cdr_ids[0])['recordings'][1]
        recording3 = self.call_logd.cdr.get_by_id(cdr_ids[1])['recordings'][0]
        recording4 = self.call_logd.cdr.get_by_id(cdr_ids[2])['recordings'][0]

        self.call_logd.cdr.delete_cdrs_recording_media([cdr_ids[0], cdr_ids[1]])

        assert_that(
            calling(self.call_logd.cdr.get_recording_media).with_args(
                cdr_ids[0], recording1['uuid']
            ),
            raises(CallLogdError).matching(
                has_properties(status_code=400, error_id='recording-media-not-found')
            ),
        )
        recordings = self.call_logd.cdr.get_by_id(cdr_ids[0])['recordings']
        assert_that(
            recordings,
            has_items(
                has_entries(uuid=recording1['uuid'], deleted=True),
                has_entries(uuid=recording2['uuid'], deleted=True),
            ),
        )

        recordings = self.call_logd.cdr.get_by_id(cdr_ids[1])['recordings']
        assert_that(
            recordings, has_item(has_entries(uuid=recording3['uuid'], deleted=True))
        )

        recordings = self.call_logd.cdr.get_by_id(cdr_ids[2])['recordings']
        assert_that(
            recordings, has_item(has_entries(uuid=recording4['uuid'], deleted=False))
        )

        response = self.call_logd.cdr.get_recording_media(
            cdr_ids[2], recording4['uuid']
        )
        assert_that(response.text, equal_to('visible'))

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    def test_delete_media_with_invalid_cdr_multi_cdr(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args([2, 3]),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=404,
                    error_id='cdr-not-found-with-given-id',
                    details=has_entries(cdr_id=2),
                ),
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/foobar.wav'}])
    def test_delete_media_with_wrong_cdr_multi_cdr(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args([2, 1]),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=404,
                    error_id='cdr-not-found-with-given-id',
                    details=has_entries(cdr_id=2),
                ),
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': None}])
    @call_log(**{'id': 2}, recordings=[{'path': None}])
    def test_delete_media_with_recording_already_deleted_multi_cdr(self):
        self.call_logd.cdr.delete_cdrs_recording_media([1, 2])
        recording = self.call_logd.cdr.get_by_id(1)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))
        recording = self.call_logd.cdr.get_by_id(2)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/denied.wav'}])
    @call_log(**{'id': 2}, recordings=[{'path': '/tmp/ok.wav'}])
    @file_('/tmp/denied.wav', mode='000', root=True)
    @file_('/tmp/ok.wav')
    def test_delete_media_when_file_has_wrong_permission_multi_cdr(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args([1, 2]),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=500,
                    error_id='recording-media-permission-denied',
                    details=has_entries(cdr_id=1),
                )
            ),
        )

    @call_log(**{'id': 1}, recordings=[{'path': '/tmp/deleted1.wav'}])
    @call_log(**{'id': 2}, recordings=[{'path': '/tmp/deleted2.wav'}])
    def test_delete_media_when_file_deleted_on_filesystem_multi_cdr(self):
        self.call_logd.cdr.delete_cdrs_recording_media([1, 2])
        recording = self.call_logd.cdr.get_by_id(1)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))
        recording = self.call_logd.cdr.get_by_id(2)['recordings'][0]
        assert_that(recording['deleted'], equal_to(True))

    @call_log(
        **{'id': 10},
        tenant_uuid=SUB_TENANT,
        recordings=[{'path': '/tmp/10-recording.wav'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=MAIN_TENANT,
        recordings=[{'path': '/tmp/11-recording.wav'}],
    )
    @file_('/tmp/10-recording.wav', content='10-recording')
    @file_('/tmp/11-recording.wav', content='11-recording')
    def test_delete_media_mutli_tenant_multi_cdr(self):
        assert_that(
            calling(self.call_logd.cdr.delete_cdrs_recording_media).with_args(
                [10, 11], tenant_uuid=SUB_TENANT
            ),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=404,
                    error_id='cdr-not-found-with-given-id',
                    details=has_entries(cdr_id=11),
                ),
            ),
        )

        recording = self.call_logd.cdr.get_by_id(10)['recordings'][0]
        assert_that(recording, has_entries(deleted=False))
        recording = self.call_logd.cdr.get_by_id(11)['recordings'][0]
        assert_that(recording, has_entries(deleted=False))

        rec_uuid = self.call_logd.cdr.get_by_id(11)['recordings'][0]['uuid']
        self.call_logd.cdr.delete_cdrs_recording_media([11], tenant_uuid=MAIN_TENANT)
        response = self.call_logd.cdr.get_by_id(11)['recordings'][0]
        assert_that(response, has_entries(uuid=rec_uuid, deleted=True))
