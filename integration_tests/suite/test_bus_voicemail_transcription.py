# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_exactly,
    has_entries,
    has_properties,
    is_,
    none,
    not_none,
)
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
            'transcription': 'Hello, this is a test voicemail.',
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
                assert_that(transcription, not_none())
                assert_that(
                    transcription,
                    has_properties(
                        voicemail_message_id=message_id,
                        tenant_uuid=USERS_TENANT,
                        voicemail_id=42,
                        transcription_text='Hello, this is a test voicemail.',
                        provider_id='openai/whisper-1',
                        language='en',
                    ),
                )

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
            'transcription': 'Minimal transcription.',
        }

        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert_that(transcription, not_none())
                assert_that(
                    transcription,
                    has_properties(
                        voicemail_message_id=message_id,
                        tenant_uuid=USERS_TENANT,
                        transcription_text='Minimal transcription.',
                        voicemail_id=none(),
                        provider_id=none(),
                        language=none(),
                    ),
                )

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
            'transcription': 'First transcription.',
            'language': 'en',
        }

        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert_that(transcription, not_none())

        until.assert_(transcription_created, tries=10, interval=1)

        # Send again with updated text — should update the existing transcription
        event_data['transcription'] = 'Updated transcription.'
        event_data['language'] = 'fr'
        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_updated():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert_that(transcription, not_none())
                assert_that(
                    transcription,
                    has_properties(
                        transcription_text='Updated transcription.',
                        language='fr',
                    ),
                )

        until.assert_(transcription_updated, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)

    @voicemail_transcription(
        voicemail_message_id='bus-test-msg-004',
        tenant_uuid=USERS_TENANT,
        transcription_text='To be deleted.',
    )
    def test_voicemail_message_deleted_removes_transcription(self, transcription):
        message_id = transcription['voicemail_message_id']

        self.bus.send_voicemail_message_deleted(message_id)

        def transcription_deleted():
            with self.database.queries() as queries:
                result = queries.find_voicemail_transcription_by_message_id(message_id)
                assert_that(result, is_(none()))

        until.assert_(transcription_deleted, tries=10, interval=1)

    @voicemail_transcription(
        voicemail_message_id='bus-test-msg-005',
        tenant_uuid=USERS_TENANT,
        transcription_text='To be deleted via global event.',
    )
    def test_global_voicemail_message_deleted_removes_transcription(
        self, transcription
    ):
        message_id = transcription['voicemail_message_id']

        self.bus.send_voicemail_message_deleted(
            message_id, event_name='global_voicemail_message_deleted'
        )

        def transcription_deleted():
            with self.database.queries() as queries:
                result = queries.find_voicemail_transcription_by_message_id(message_id)
                assert_that(result, is_(none()))

        until.assert_(transcription_deleted, tries=10, interval=1)

    def test_voicemail_message_deleted_nonexistent_is_noop(self):
        self.bus.send_voicemail_message_deleted('nonexistent-msg-id')
        message_id = 'bus-test-msg-006'
        event_data = {
            'message_id': message_id,
            'tenant_uuid': str(USERS_TENANT),
            'transcription': 'Still alive.',
        }
        self.bus.send_voicemail_transcription_completed(event_data)

        def transcription_created():
            with self.database.queries() as queries:
                transcription = queries.find_voicemail_transcription_by_message_id(
                    message_id
                )
                assert_that(transcription, not_none())

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
            'transcription': 'Check bus event.',
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
                assert_that(transcription, not_none())

        until.assert_(transcription_created, tries=10, interval=1)

        def event_received():
            events = accumulator.accumulate(with_headers=True)
            assert_that(
                events,
                contains_exactly(
                    has_entries(
                        message=has_entries(
                            data=has_entries(voicemail_message_id=message_id),
                        ),
                        headers=has_entries(
                            name='call_logd_voicemail_transcription_created',
                            tenant_uuid=str(USERS_TENANT),
                        ),
                    ),
                ),
            )

        until.assert_(event_received, tries=10, interval=1)

        with self.database.queries() as queries:
            transcription = queries.find_voicemail_transcription_by_message_id(
                message_id
            )
            if transcription:
                queries.delete_voicemail_transcription(transcription.uuid)
