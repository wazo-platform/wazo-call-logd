# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_test_helpers import until

from .helpers.base import IntegrationTest
from .helpers.constants import USERS_TENANT
from .helpers.database import voicemail_transcription
from .helpers.wait_strategy import CallLogdComponentsWaitStrategy


class TestBusVoicemailTranscription(IntegrationTest):
    wait_strategy = CallLogdComponentsWaitStrategy(["bus_consumer"])

    def test_transcription_completed_creates_transcription(self):
        message_id = 'bus-test-msg-001'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'voicemail_id': 42,
            'transcription_text': 'Hello, this is a test voicemail.',
            'provider_id': 'openai/whisper-1',
            'language': 'en',
            'duration': 15.5,
        }

        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None
                assert transcription.message_id == message_id
                assert transcription.tenant_uuid == USERS_TENANT
                assert transcription.voicemail_id == 42
                assert (
                    transcription.transcription_text
                    == 'Hello, this is a test voicemail.'
                )
                assert transcription.provider_id == 'openai/whisper-1'
                assert transcription.language == 'en'

        until.assert_(transcription_created, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)

    def test_transcription_completed_minimal_fields(self):
        message_id = 'bus-test-msg-002'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'transcription_text': 'Minimal transcription.',
        }

        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None
                assert transcription.message_id == message_id
                assert transcription.tenant_uuid == USERS_TENANT
                assert transcription.transcription_text == 'Minimal transcription.'
                assert transcription.voicemail_id is None
                assert transcription.provider_id is None
                assert transcription.language is None

        until.assert_(transcription_created, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)

    def test_transcription_completed_duplicate_updates(self):
        message_id = 'bus-test-msg-003'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'transcription_text': 'First transcription.',
            'language': 'en',
        }

        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None

        until.assert_(transcription_created, tries=10, interval=1)

        # Send again with updated text — should update the existing transcription
        event_data['transcription_text'] = 'Updated transcription.'
        event_data['language'] = 'fr'
        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_updated():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None
                assert transcription.transcription_text == 'Updated transcription.'
                assert transcription.language == 'fr'

        until.assert_(transcription_updated, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)

    @voicemail_transcription(
        message_id='bus-test-msg-004',
        tenant_uuid=USERS_TENANT,
        transcription_text='To be deleted.',
    )
    def test_voicemail_message_deleted_removes_transcription(self, transcription):
        message_id = transcription['message_id']

        self.bus.send_voicemail_message_deleted(message_id)

        def transcription_deleted():
            with self.database.queries() as queries:
                result = queries.find_voicemail_transcription_by_message_id(message_id)
                assert result is None

        until.assert_(transcription_deleted, tries=10, interval=1)

    @voicemail_transcription(
        message_id='bus-test-msg-005',
        tenant_uuid=USERS_TENANT,
        transcription_text='To be deleted via global event.',
    )
    def test_global_voicemail_message_deleted_removes_transcription(
        self, transcription
    ):
        message_id = transcription['message_id']

        self.bus.send_voicemail_message_deleted(
            message_id, event_name='global_voicemail_message_deleted'
        )

        def transcription_deleted():
            with self.database.queries() as queries:
                result = queries.find_voicemail_transcription_by_message_id(message_id)
                assert result is None

        until.assert_(transcription_deleted, tries=10, interval=1)

    def test_voicemail_message_deleted_nonexistent_is_noop(self):
        self.bus.send_voicemail_message_deleted('nonexistent-msg-id')
        message_id = 'bus-test-msg-006'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'transcription_text': 'Still alive.',
        }
        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None

        until.assert_(transcription_created, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)

    def test_transcription_created_bus_event_published(self):
        message_id = 'bus-test-msg-007'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'transcription_text': 'Check bus event.',
            'voicemail_id': 99,
        }

        accumulator = self.bus.accumulator(
            headers={'name': 'call_logd_voicemail_transcription_created'}
        )
        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert transcription is not None

        until.assert_(transcription_created, tries=10, interval=1)

        def event_received():
            events = accumulator.accumulate(with_headers=True)
            assert len(events) == 1
            event = events[0]
            assert event['message']['data']['message_id'] == message_id
            assert (
                event['headers']['name'] == 'call_logd_voicemail_transcription_created'
            )
            assert event['headers']['tenant_uuid'] == str(USERS_TENANT)

        until.assert_(event_received, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)
