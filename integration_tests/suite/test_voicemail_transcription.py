# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from wazo_call_logd_client.exceptions import CallLogdError

from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TOKEN, USERS_TENANT
from .helpers.database import voicemail_transcription


class TestInputParameters(IntegrationTest):
    def test_list_transcriptions_with_wrong_parameters_returns_400(self):
        self.call_logd.set_token(MASTER_TOKEN)
        erroneous_bodies = [
            # limit
            {'limit': 'abcd'},
            {'limit': -1},
            {'limit': '12:345'},
            # offset
            {'offset': 'abcd'},
            {'offset': -1},
            {'offset': '12:345'},
            # direction
            {'direction': 'abcd'},
            {'direction': 'ascending'},
            {'direction': 'DESC'},
            # order
            {'order': 'abcd'},
            {'order': 'unknown_field'},
            {'order': 'tenant_uuid'},
            # from
            {'from_': 'abcd'},
            {'from_': '12:345'},
            {'from_': '2017-042-10'},
            # until
            {'until': 'abcd'},
            {'until': '12:345'},
            {'until': '2017-042-10'},
        ]
        for body in erroneous_bodies:
            with pytest.raises(CallLogdError) as exc_info:
                self.call_logd.voicemail_transcription.list_transcriptions(**body)
            assert exc_info.value.status_code == 400, body


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
        assert result['total'] == 2
        message_ids = {item['message_id'] for item in result['items']}
        assert '1234567890-0000000050' in message_ids
        assert '1234567890-0000000051' in message_ids

    @voicemail_transcription(
        message_id='1234567890-0000000040',
        tenant_uuid=str(USERS_TENANT),
        transcription_text='Check fields',
    )
    def test_response_fields(self, _):
        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.voicemail_transcription.list_transcriptions()
        item = result['items'][0]
        assert 'message_id' in item
        assert 'voicemail_id' in item
        assert 'provider_id' in item
        assert 'transcription_text' in item
        assert 'language' in item
        assert 'duration' in item
        assert 'created_at' in item

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
        assert result['total'] == 2
        message_ids = {item['message_id'] for item in result['items']}
        assert '1234567890-0000000060' in message_ids
        assert '1234567890-0000000062' in message_ids

        # Filter by multiple voicemail_id (comma-separated)
        result = self.call_logd.voicemail_transcription.list_transcriptions(
            voicemail_id='100,200',
        )
        assert result['total'] == 3

        # Filter with no match
        result = self.call_logd.voicemail_transcription.list_transcriptions(
            voicemail_id=999,
        )
        assert result['total'] == 0
