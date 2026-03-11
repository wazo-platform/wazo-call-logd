# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, equal_to, has_entries, has_items, has_key, not_

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TOKEN, USERS_TENANT
from .helpers.database import voicemail_transcription


class TestVoicemailTranscription(IntegrationTest):
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000050',
        tenant_uuid=str(USERS_TENANT),
        transcription_text='Admin list all',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000051',
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
                has_entries(voicemail_message_id='1234567890-0000000050'),
                has_entries(voicemail_message_id='1234567890-0000000051'),
            ),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000040',
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
        assert_that(item, has_key('voicemail_message_id'))
        assert_that(item, has_key('voicemail_id'))
        assert_that(item, has_key('provider_id'))
        assert_that(item, has_key('transcript'))
        assert_that(item, has_key('language'))
        assert_that(item, has_key('duration'))
        assert_that(item, has_key('created_at'))
