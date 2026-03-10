# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    empty,
    equal_to,
    has_entries,
    has_items,
    has_key,
    has_length,
    has_properties,
    not_,
)
from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import IntegrationTest
from .helpers.constants import (
    MASTER_TOKEN,
    OTHER_USER_TOKEN,
    USER_1_TOKEN,
    USER_1_UUID,
    USER_2_TOKEN,
    USERS_TENANT,
)
from .helpers.database import voicemail_transcription


class TestVoicemailTranscription(IntegrationTest):
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000001',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Hello from user 1',
        language='en',
        duration=10.5,
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000002',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Hello from user 1 again',
    )
    def test_list_user_me_transcriptions(self, _, __):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.voicemail_transcription.list_from_user()
        assert_that(result['total'], equal_to(2))
        assert_that(
            result['items'],
            has_items(
                has_entries(
                    voicemail_message_id='1234567890-0000000001',
                    transcript='Hello from user 1',
                    language='en',
                    duration=10.5,
                )
            ),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000010',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='No messages for me',
    )
    def test_list_user_me_transcriptions_other_user_sees_nothing(self, _):
        self.call_logd.set_token(USER_2_TOKEN)
        result = self.call_logd.voicemail_transcription.list_from_user()
        assert_that(result['total'], equal_to(0))
        assert_that(result['items'], empty())

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000003',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Specific voicemail',
        language='fr',
        duration=25.0,
    )
    def test_get_user_me_transcription(self, _):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.voicemail_transcription.get_from_user(
            '1234567890-0000000003'
        )
        assert_that(
            result,
            has_entries(
                voicemail_message_id='1234567890-0000000003',
                transcript='Specific voicemail',
                language='fr',
                duration=25.0,
            ),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000004',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Not for user 2',
    )
    def test_get_user_me_transcription_wrong_user(self, _):
        self.call_logd.set_token(USER_2_TOKEN)
        assert_that(
            calling(self.call_logd.voicemail_transcription.get_from_user).with_args(
                '1234567890-0000000004'
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    def test_get_user_me_transcription_not_found(self):
        self.call_logd.set_token(USER_1_TOKEN)
        assert_that(
            calling(self.call_logd.voicemail_transcription.get_from_user).with_args(
                '9999999999-9999999999'
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000005',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Admin can see this',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000006',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Admin can also see this',
    )
    def test_list_user_transcriptions_as_admin(self, _, __):
        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.voicemail_transcription.list_for_user(str(USER_1_UUID))
        assert_that(result['total'], equal_to(2))
        assert_that(
            result['items'],
            has_items(
                has_entries(voicemail_message_id='1234567890-0000000005'),
                has_entries(voicemail_message_id='1234567890-0000000006'),
            ),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000007',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Admin gets single transcription',
    )
    def test_get_user_transcription_as_admin(self, _):
        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.voicemail_transcription.get_for_user(
            str(USER_1_UUID), '1234567890-0000000007'
        )
        assert_that(
            result,
            has_entries(
                voicemail_message_id='1234567890-0000000007',
                transcript='Admin gets single transcription',
            ),
        )

    def test_get_user_transcription_not_found(self):
        self.call_logd.set_token(MASTER_TOKEN)
        assert_that(
            calling(self.call_logd.voicemail_transcription.get_for_user).with_args(
                str(USER_1_UUID), '9999999999-9999999999'
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000009',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Tenant isolated',
    )
    def test_get_transcription_wrong_tenant(self, _):
        self.call_logd.set_token(OTHER_USER_TOKEN)
        assert_that(
            calling(self.call_logd.voicemail_transcription.get_for_user).with_args(
                str(USER_1_UUID), '1234567890-0000000009'
            ),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000020',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Please call me back about the invoice',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000021',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Happy birthday, have a great day',
    )
    def test_list_user_me_transcriptions_with_search(self, _, __):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.voicemail_transcription.list_from_user(
            search_text='invoice'
        )
        assert_that(result['total'], equal_to(1))
        assert_that(
            result['items'],
            has_items(has_entries(voicemail_message_id='1234567890-0000000020')),
        )

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000030',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='First',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000031',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Second',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000032',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Third',
    )
    def test_list_transcriptions_with_pagination(self, _, __, ___):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.voicemail_transcription.list_from_user(
            limit=1, offset=0
        )
        assert_that(result['total'], equal_to(3))
        assert_that(result['items'], has_length(1))

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000040',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Check fields',
    )
    def test_response_fields(self, _):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.voicemail_transcription.get_from_user(
            '1234567890-0000000040'
        )
        assert_that(result, not_(has_key('uuid')))
        assert_that(result, not_(has_key('status')))
        assert_that(result, not_(has_key('user_uuid')))
        assert_that(result, has_key('voicemail_message_id'))
        assert_that(result, has_key('voicemail_id'))
        assert_that(result, has_key('provider_id'))
        assert_that(result, has_key('transcript'))
        assert_that(result, has_key('language'))
        assert_that(result, has_key('duration'))
        assert_that(result, has_key('created_at'))

    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000050',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
        transcription_text='Admin list all',
    )
    @voicemail_transcription(
        voicemail_message_id='1234567890-0000000051',
        tenant_uuid=str(USERS_TENANT),
        user_uuid=str(USER_1_UUID),
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
