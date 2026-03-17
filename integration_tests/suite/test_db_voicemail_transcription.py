# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.database.models import VoicemailTranscription

from .helpers.base import DBIntegrationTest
from .helpers.constants import MASTER_TENANT, OTHER_TENANT
from .helpers.database import voicemail_transcription


class TestDBVoicemailTranscription(DBIntegrationTest):
    def test_create(self):
        body = {
            'message_id': '0000000001-0000000001',
            'tenant_uuid': MASTER_TENANT,
            'voicemail_id': 42,
            'transcription_text': 'Hello world',
            'provider_id': 'openai/whisper-1',
            'language': 'en',
            'duration': 10.5,
        }
        result = self.dao.voicemail_transcription.create(body)
        assert result.uuid is not None
        for key, value in body.items():
            assert getattr(result, key) == value

        self.session.query(VoicemailTranscription).delete()
        self.session.commit()

    @voicemail_transcription(
        message_id='0000000002-0000000001',
    )
    def test_get_by_message_id(self, transcription):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000002-0000000001'
        )
        assert result.message_id == '0000000002-0000000001'

    def test_get_by_message_id_not_found(self):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '9999999999-9999999999'
        )
        assert result is None

    @voicemail_transcription(
        message_id='0000000003-0000000001',
        tenant_uuid=str(MASTER_TENANT),
    )
    def test_get_by_message_id_tenant_filter(self, _):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000003-0000000001', tenant_uuids=[MASTER_TENANT]
        )
        assert result is not None

        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000003-0000000001', tenant_uuids=[OTHER_TENANT]
        )
        assert result is None

    @voicemail_transcription(
        message_id='0000000005-0000000001',
        transcription_text='First message',
    )
    @voicemail_transcription(
        message_id='0000000005-0000000002',
        transcription_text='Second message',
    )
    @voicemail_transcription(
        message_id='0000000005-0000000003',
        transcription_text='Third message',
    )
    def test_find_all(self, _, __, ___):
        result = self.dao.voicemail_transcription.find_all(tenant_uuids=[MASTER_TENANT])
        assert result['total'] == 3
        assert len(result['items']) == 3

    @voicemail_transcription(
        message_id='0000000006-0000000003',
        voicemail_id=100,
        transcription_text='VM 100 msg',
    )
    @voicemail_transcription(
        message_id='0000000006-0000000004',
        voicemail_id=200,
        transcription_text='VM 200 msg',
    )
    def test_find_all_voicemail_id_filter(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], voicemail_id=[100]
        )
        assert result['total'] == 2
        assert result['filtered'] == 1
        assert result['items'][0].message_id == '0000000006-0000000003'

    @voicemail_transcription(
        message_id='0000000007-0000000001',
        transcription_text='Call me about the invoice',
    )
    @voicemail_transcription(
        message_id='0000000007-0000000002',
        transcription_text='Happy birthday',
    )
    def test_find_all_search(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], search_text='invoice'
        )
        assert result['total'] == 2
        assert result['filtered'] == 1
        assert result['items'][0].message_id == '0000000007-0000000001'

    @voicemail_transcription(
        message_id='0000000007-0000000003',
        transcription_text='50% discount available',
    )
    @voicemail_transcription(
        message_id='0000000007-0000000004',
        transcription_text='50 dollars discount available',
    )
    def test_find_all_search_with_percent(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], search_text='50%'
        )
        assert result['total'] == 1
        assert result['items'][0].message_id == '0000000007-0000000003'

    @voicemail_transcription(
        message_id='0000000007-0000000005',
        transcription_text='use snake_case naming',
    )
    @voicemail_transcription(
        message_id='0000000007-0000000006',
        transcription_text='use snakeXcase naming',
    )
    def test_find_all_search_with_underscore(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], search_text='snake_case'
        )
        assert result['total'] == 1
        assert result['items'][0].message_id == '0000000007-0000000005'

    @voicemail_transcription(
        message_id='0000000008-0000000001',
        transcription_text='A',
    )
    @voicemail_transcription(
        message_id='0000000008-0000000002',
        transcription_text='B',
    )
    @voicemail_transcription(
        message_id='0000000008-0000000003',
        transcription_text='C',
    )
    def test_find_all_pagination(self, _, __, ___):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], limit=2, offset=0
        )
        assert result['total'] == 3
        assert len(result['items']) == 2

        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], limit=2, offset=2
        )
        assert len(result['items']) == 1

    @voicemail_transcription(
        message_id='0000000008-0000000004',
        transcription_text='D',
    )
    @voicemail_transcription(
        message_id='0000000008-0000000005',
        transcription_text='E',
    )
    def test_find_all_pagination_limit_zero(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], limit=0
        )
        assert result['total'] == 2
        assert len(result['items']) == 0

    @voicemail_transcription(
        message_id='0000000008-0000000006',
        transcription_text='F',
    )
    @voicemail_transcription(
        message_id='0000000008-0000000007',
        transcription_text='G',
    )
    def test_find_all_pagination_offset_zero(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], offset=0
        )
        assert result['total'] == 2
        assert len(result['items']) == 2

    @voicemail_transcription(
        message_id='0000000009-0000000001',
    )
    def test_delete_by_message_id(self, _):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000009-0000000001'
        )
        assert result is True

        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000009-0000000001'
        )
        assert result is None

    def test_delete_by_message_id_not_found(self):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '9999999999-9999999999'
        )
        assert result is False

    @voicemail_transcription(
        message_id='0000000010-0000000001',
        tenant_uuid=str(MASTER_TENANT),
    )
    def test_delete_by_message_id_tenant_filter(self, _):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000010-0000000001', tenant_uuids=[OTHER_TENANT]
        )
        assert result is False

        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000010-0000000001', tenant_uuids=[MASTER_TENANT]
        )
        assert result is True
