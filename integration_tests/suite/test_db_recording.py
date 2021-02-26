# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid

from datetime import (
    timedelta as td,
    timezone as tz,
)
from hamcrest import (
    assert_that,
    contains_inanyorder,
    has_properties,
    none,
)

from wazo_call_logd.database.models import Recording

from .helpers.base import DBIntegrationTest
from .helpers.database import recording, call_log


class TestRecording(DBIntegrationTest):
    @call_log(**{'id': 1})
    @call_log(**{'id': 2})
    @recording(call_log_id=1, path='rec1')
    @recording(call_log_id=2, path='rec2')
    def test_delete_media_by_recording_uuid(self, rec1, rec2):
        self.dao.recording.delete_media_by(uuid=rec1['uuid'])

        result = self.session.query(Recording).all()
        assert_that(
            result,
            contains_inanyorder(
                has_properties(uuid=rec1['uuid'], path=None),
                has_properties(uuid=rec2['uuid'], path='rec2'),
            ),
        )

    @call_log(**{'id': 1})
    @call_log(**{'id': 2})
    @recording(call_log_id=1, path='rec1')
    @recording(call_log_id=2, path='rec2')
    @recording(call_log_id=2, path='rec3')
    def test_delete_media_by_call_log_id(self, rec1, rec2, rec3):
        self.dao.recording.delete_media_by(call_log_id=rec2['call_log_id'])

        result = self.session.query(Recording).all()
        assert_that(
            result,
            contains_inanyorder(
                has_properties(uuid=rec1['uuid'], path='rec1'),
                has_properties(uuid=rec2['uuid'], path=None),
                has_properties(uuid=rec3['uuid'], path=None),
            ),
        )

    @call_log(**{'id': 1})
    @call_log(**{'id': 2})
    @call_log(**{'id': 3})
    @recording(call_log_id=1, path='rec1')
    @recording(call_log_id=2, path='rec2')
    @recording(call_log_id=2, path='rec3')
    @recording(call_log_id=3, path='rec4')
    def test_delete_media_by_call_log_ids(self, rec1, rec2, rec3, rec4):
        self.dao.recording.delete_media_by(
            call_log_ids=[rec1['call_log_id'], rec2['call_log_id']]
        )

        result = self.session.query(Recording).all()
        assert_that(
            result,
            contains_inanyorder(
                has_properties(uuid=rec1['uuid'], path=None),
                has_properties(uuid=rec2['uuid'], path=None),
                has_properties(uuid=rec3['uuid'], path=None),
                has_properties(uuid=rec4['uuid'], path='rec4'),
            ),
        )

    @call_log(**{'id': 1})
    @call_log(**{'id': 2})
    @recording(call_log_id=1)
    @recording(call_log_id=2)
    def test_find_by(self, rec1, rec2):
        result = self.dao.recording.find_by(uuid=rec2['uuid'])
        assert_that(result, has_properties(uuid=rec2['uuid']))

        result = self.dao.recording.find_by(call_log_id=rec2['call_log_id'])
        assert_that(result, has_properties(uuid=rec2['uuid']))

        result = self.dao.recording.find_by(uuid=uuid.uuid4())
        assert_that(result, none())

        result = self.dao.recording.find_by(call_log_id=666)
        assert_that(result, none())

        result = self.dao.recording.find_by(
            uuid=rec1['uuid'], call_log_id=rec2['call_log_id']
        )
        assert_that(result, none())

    @call_log(**{'id': 1})
    @recording(call_log_id=1)
    def test_recording_filename(self, rec):
        recording_uuid = rec['uuid']
        result = self.dao.recording.find_by(uuid=recording_uuid)
        offset = rec['start_time'].utcoffset() or td(seconds=0)
        date_utc = (rec['start_time'] - offset).replace(tzinfo=tz.utc)
        start = date_utc.strftime('%Y-%m-%dT%H_%M_%SUTC')
        assert_that(result, has_properties(filename=f'{start}-1-{recording_uuid}.wav'))
