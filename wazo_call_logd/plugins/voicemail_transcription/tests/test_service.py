# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock

from hamcrest import assert_that, calling, equal_to, is_, none, raises
from sqlalchemy.exc import IntegrityError

from wazo_call_logd.plugins.voicemail_transcription.exceptions import (
    TranscriptionNotFoundException,
)
from wazo_call_logd.plugins.voicemail_transcription.service import TranscriptionService

TENANT_UUID = '11111111-2222-3333-4444-555555555555'
USER_UUID = '66666666-7777-8888-9999-aaaaaaaaaaaa'


class TestTranscriptionService(TestCase):
    def setUp(self):
        self.dao = Mock()
        self.notifier = Mock()
        self.service = TranscriptionService(self.dao, self.notifier)

    def test_create_transcription(self):
        self.dao.voicemail_transcription.create.return_value = Mock(
            voicemail_message_id='msg-123'
        )

        result = self.service.create_transcription(
            voicemail_message_id='msg-123',
            tenant_uuid=TENANT_UUID,
            user_uuid=USER_UUID,
            transcription_text='Hello world',
            provider_id='openai/whisper-1',
            language='en',
            duration=10.5,
        )

        self.dao.voicemail_transcription.create.assert_called_once()
        self.notifier.created.assert_called_once_with(
            self.dao.voicemail_transcription.create.return_value
        )
        assert_that(result, is_(self.dao.voicemail_transcription.create.return_value))

    def test_create_transcription_duplicate(self):
        self.dao.voicemail_transcription.create.side_effect = IntegrityError(
            'duplicate', {}, None
        )

        result = self.service.create_transcription(
            voicemail_message_id='msg-123',
            tenant_uuid=TENANT_UUID,
            user_uuid=USER_UUID,
            transcription_text='Hello world',
        )

        assert_that(result, is_(none()))
        self.notifier.created.assert_not_called()

    def test_get_transcription_found(self):
        expected = Mock(voicemail_message_id='msg-123')
        self.dao.voicemail_transcription.get_by_message_id.return_value = expected

        result = self.service.get_transcription('msg-123', tenant_uuids=[TENANT_UUID])

        self.dao.voicemail_transcription.get_by_message_id.assert_called_once_with(
            'msg-123', tenant_uuids=[TENANT_UUID], user_uuid=None
        )
        assert_that(result, equal_to(expected))

    def test_get_transcription_not_found(self):
        self.dao.voicemail_transcription.get_by_message_id.return_value = None

        assert_that(
            calling(self.service.get_transcription).with_args('msg-123'),
            raises(TranscriptionNotFoundException),
        )

    def test_get_transcription_wrong_tenant(self):
        self.dao.voicemail_transcription.get_by_message_id.return_value = None

        assert_that(
            calling(self.service.get_transcription).with_args(
                'msg-123', tenant_uuids=['other-tenant']
            ),
            raises(TranscriptionNotFoundException),
        )

    def test_get_transcription_wrong_user(self):
        self.dao.voicemail_transcription.get_by_message_id.return_value = None

        assert_that(
            calling(self.service.get_transcription).with_args(
                'msg-123', user_uuid='wrong-user'
            ),
            raises(TranscriptionNotFoundException),
        )

    def test_list_transcriptions(self):
        expected = {'items': [], 'total': 0, 'filtered': 0}
        self.dao.voicemail_transcription.find_all.return_value = expected

        result = self.service.list_transcriptions(
            tenant_uuids=[TENANT_UUID], limit=10, offset=0
        )

        self.dao.voicemail_transcription.find_all.assert_called_once_with(
            tenant_uuids=[TENANT_UUID], user_uuid=None, limit=10, offset=0
        )
        assert_that(result, equal_to(expected))

    def test_delete_transcription_found(self):
        transcription = Mock(voicemail_message_id='msg-123', tenant_uuid=TENANT_UUID)
        self.dao.voicemail_transcription.get_by_message_id.return_value = transcription
        self.dao.voicemail_transcription.delete_by_message_id.return_value = True

        result = self.service.delete_transcription('msg-123')

        self.dao.voicemail_transcription.delete_by_message_id.assert_called_once_with(
            'msg-123', tenant_uuids=None, user_uuid=None
        )
        self.notifier.deleted.assert_called_once_with('msg-123', TENANT_UUID)
        assert_that(result, is_(True))

    def test_delete_transcription_not_found(self):
        self.dao.voicemail_transcription.get_by_message_id.return_value = None

        result = self.service.delete_transcription('msg-999')

        assert_that(result, is_(False))
        self.notifier.deleted.assert_not_called()
