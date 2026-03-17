# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock

from hamcrest import assert_that, calling, equal_to, is_, raises
from sqlalchemy.exc import IntegrityError

from wazo_call_logd.plugins.voicemail_transcription.exceptions import (
    TranscriptionNotFoundException,
)
from wazo_call_logd.plugins.voicemail_transcription.service import TranscriptionService

TENANT_UUID = '11111111-2222-3333-4444-555555555555'


class TestTranscriptionService(TestCase):
    def setUp(self):
        self.dao = Mock()
        self.notifier = Mock()
        self.service = TranscriptionService(self.dao, self.notifier)

    def test_create_transcription(self):
        self.dao.voicemail_transcription.create.return_value = Mock(
            message_id='msg-123'
        )

        result = self.service.create_transcription(
            message_id='msg-123',
            tenant_uuid=TENANT_UUID,
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

    def test_create_transcription_duplicate_updates(self):
        existing = Mock(uuid='existing-uuid', message_id='msg-123')
        updated = Mock(message_id='msg-123')
        orig = Mock(pgcode='23505')
        self.dao.voicemail_transcription.create.side_effect = IntegrityError(
            'duplicate', {}, orig
        )
        self.dao.voicemail_transcription.get_by_message_id.return_value = existing
        self.dao.voicemail_transcription.update.return_value = updated

        result = self.service.create_transcription(
            message_id='msg-123',
            tenant_uuid=TENANT_UUID,
            transcription_text='Hello world',
        )

        self.dao.voicemail_transcription.get_by_message_id.assert_called_once_with(
            'msg-123', tenant_uuids=[TENANT_UUID]
        )
        self.dao.voicemail_transcription.update.assert_called_once()
        self.notifier.created.assert_called_once_with(updated)
        assert_that(result, is_(updated))

    def test_create_transcription_non_unique_integrity_error_raises(self):
        orig = Mock(pgcode='23503')
        self.dao.voicemail_transcription.create.side_effect = IntegrityError(
            'foreign key violation', {}, orig
        )

        assert_that(
            calling(self.service.create_transcription).with_args(
                message_id='msg-123',
                tenant_uuid=TENANT_UUID,
                transcription_text='Hello world',
            ),
            raises(IntegrityError),
        )

    def test_list_transcriptions(self):
        expected = {'items': [], 'total': 0, 'filtered': 0}
        self.dao.voicemail_transcription.find_all.return_value = expected

        result = self.service.list_transcriptions(
            tenant_uuids=[TENANT_UUID], limit=10, offset=0
        )

        self.dao.voicemail_transcription.find_all.assert_called_once_with(
            tenant_uuids=[TENANT_UUID], limit=10, offset=0
        )
        assert_that(result, equal_to(expected))

    def test_delete_transcription_found(self):
        transcription = Mock(message_id='msg-123', tenant_uuid=TENANT_UUID)
        self.dao.voicemail_transcription.get_by_message_id.return_value = transcription
        self.dao.voicemail_transcription.delete_by_message_id.return_value = True

        result = self.service.delete_transcription('msg-123')

        self.dao.voicemail_transcription.delete_by_message_id.assert_called_once_with(
            'msg-123', tenant_uuids=None
        )
        self.notifier.deleted.assert_called_once_with('msg-123', TENANT_UUID)
        assert_that(result, is_(True))

    def test_delete_transcription_not_found(self):
        self.dao.voicemail_transcription.get_by_message_id.return_value = None

        assert_that(
            calling(self.service.delete_transcription).with_args('msg-999'),
            raises(TranscriptionNotFoundException),
        )
        self.notifier.deleted.assert_not_called()
