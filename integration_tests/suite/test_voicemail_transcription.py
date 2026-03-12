# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, equal_to, has_entries, has_items, has_key, not_

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TOKEN, USERS_TENANT
from .helpers.database import voicemail_transcription


class TestVoicemailTranscription(IntegrationTest):
    @voicemail_transcription(
        message_id='1234567890-0000000050',
        tenant_uuid=str(USERS_TENANT),
        transcription_text='Admin list all',
    )
    @voicemail_transcription(
        message_id='1234567890-0000000051',
        tenant_uuid=str(USERS_TENANT),
        transcription_text='Admin list all 2',
    )
    def test_list_transcriptions_as_admin(self, _, __):
        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.voicemail_transcription.list_transcriptions()
        assert_that(result['total'], equal_to(2))
        assert_that(
            result['items'],
            has_items(
                has_entries(message_id='1234567890-0000000050'),
                has_entries(message_id='1234567890-0000000051'),
            ),
        )

    @voicemail_transcription(
        message_id='1234567890-0000000040',
        tenant_uuid=str(USERS_TENANT),
        transcription_text='Check fields',
    )
    def test_response_fields(self, _):
        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.voicemail_transcription.list_transcriptions()
        item = result['items'][0]
        assert_that(item, not_(has_key('uuid')))
        assert_that(item, not_(has_key('status')))
        assert_that(item, not_(has_key('user_uuid')))
        assert_that(item, has_key('message_id'))
        assert_that(item, has_key('voicemail_id'))
        assert_that(item, has_key('provider_id'))
        assert_that(item, has_key('transcription_text'))
        assert_that(item, has_key('language'))
        assert_that(item, has_key('duration'))
        assert_that(item, has_key('created_at'))

    @voicemail_transcription(
        message_id='1234567890-0000000060',
        tenant_uuid=str(USERS_TENANT),
        voicemail_id=100,
        transcription_text='VM 100 first',
    )
    @voicemail_transcription(
        message_id='1234567890-0000000061',
        tenant_uuid=str(USERS_TENANT),
        voicemail_id=200,
        transcription_text='VM 200 msg',
    )
    @voicemail_transcription(
        message_id='1234567890-0000000062',
        tenant_uuid=str(USERS_TENANT),
        voicemail_id=100,
        transcription_text='VM 100 second',
    )
    def test_list_filter_by_voicemail_id(self, _, __, ___):
        self.call_logd.set_token(MASTER_TOKEN)

        # Filter by single voicemail_id
        result = self.call_logd.voicemail_transcription.list_transcriptions(
            voicemail_id=100,
        )
        assert_that(result['total'], equal_to(2))
        assert_that(
            result['items'],
            has_items(
                has_entries(message_id='1234567890-0000000060'),
                has_entries(message_id='1234567890-0000000062'),
            ),
        )

        # Filter by multiple voicemail_id (comma-separated)
        result = self.call_logd.voicemail_transcription.list_transcriptions(
            voicemail_id='100,200',
        )
        assert_that(result['total'], equal_to(3))

        # Filter with no match
        result = self.call_logd.voicemail_transcription.list_transcriptions(
            voicemail_id=999,
        )
        assert_that(result['total'], equal_to(0))
