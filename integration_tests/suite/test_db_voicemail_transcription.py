# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, equal_to, has_length, has_properties, none, not_none

from wazo_call_logd.database.models import VoicemailTranscription

from .helpers.base import DBIntegrationTest
from .helpers.constants import MASTER_TENANT, OTHER_TENANT
from .helpers.database import voicemail_transcription


class TestDBVoicemailTranscription(DBIntegrationTest):
    def test_create(self):
        body = {
            'voicemail_message_id': '0000000001-0000000001',
            'tenant_uuid': MASTER_TENANT,
            'voicemail_id': 42,
            'transcription_text': 'Hello world',
            'provider_id': 'openai/whisper-1',
            'language': 'en',
            'duration': 10.5,
        }
        result = self.dao.voicemail_transcription.create(body)
        assert_that(result, has_properties(uuid=not_none(), **body))

        self.session.query(VoicemailTranscription).delete()
        self.session.commit()

    @voicemail_transcription(
        voicemail_message_id='0000000002-0000000001',
    )
    def test_get_by_message_id(self, transcription):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000002-0000000001'
        )
        assert_that(
            result,
            has_properties(
                voicemail_message_id='0000000002-0000000001',
            ),
        )

    def test_get_by_message_id_not_found(self):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '9999999999-9999999999'
        )
        assert_that(result, none())

    @voicemail_transcription(
        voicemail_message_id='0000000003-0000000001',
        tenant_uuid=str(MASTER_TENANT),
    )
    def test_get_by_message_id_tenant_filter(self, _):
        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000003-0000000001', tenant_uuids=[MASTER_TENANT]
        )
        assert_that(result, not_none())

        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000003-0000000001', tenant_uuids=[OTHER_TENANT]
        )
        assert_that(result, none())

    @voicemail_transcription(
        voicemail_message_id='0000000005-0000000001',
        transcription_text='First message',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000005-0000000002',
        transcription_text='Second message',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000005-0000000003',
        transcription_text='Third message',
    )
    def test_find_all(self, _, __, ___):
        result = self.dao.voicemail_transcription.find_all(tenant_uuids=[MASTER_TENANT])
        assert_that(result['total'], equal_to(3))
        assert_that(result['items'], has_length(3))

    @voicemail_transcription(
        voicemail_message_id='0000000006-0000000003',
        voicemail_id=100,
        transcription_text='VM 100 msg',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000006-0000000004',
        voicemail_id=200,
        transcription_text='VM 200 msg',
    )
    def test_find_all_voicemail_id_filter(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], voicemail_id=[100]
        )
        assert_that(result['total'], equal_to(1))
        assert_that(
            result['items'][0],
            has_properties(voicemail_message_id='0000000006-0000000003'),
        )

    @voicemail_transcription(
        voicemail_message_id='0000000007-0000000001',
        transcription_text='Call me about the invoice',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000007-0000000002',
        transcription_text='Happy birthday',
    )
    def test_find_all_search(self, _, __):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], search_text='invoice'
        )
        assert_that(result['total'], equal_to(1))
        assert_that(
            result['items'][0],
            has_properties(voicemail_message_id='0000000007-0000000001'),
        )

    @voicemail_transcription(
        voicemail_message_id='0000000008-0000000001',
        transcription_text='A',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000008-0000000002',
        transcription_text='B',
    )
    @voicemail_transcription(
        voicemail_message_id='0000000008-0000000003',
        transcription_text='C',
    )
    def test_find_all_pagination(self, _, __, ___):
        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], limit=2, offset=0
        )
        assert_that(result['total'], equal_to(3))
        assert_that(result['items'], has_length(2))

        result = self.dao.voicemail_transcription.find_all(
            tenant_uuids=[MASTER_TENANT], limit=2, offset=2
        )
        assert_that(result['items'], has_length(1))

    @voicemail_transcription(
        voicemail_message_id='0000000009-0000000001',
    )
    def test_delete_by_message_id(self, _):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000009-0000000001'
        )
        assert_that(result, equal_to(True))

        result = self.dao.voicemail_transcription.get_by_message_id(
            '0000000009-0000000001'
        )
        assert_that(result, none())

    def test_delete_by_message_id_not_found(self):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '9999999999-9999999999'
        )
        assert_that(result, equal_to(False))

    @voicemail_transcription(
        voicemail_message_id='0000000010-0000000001',
        tenant_uuid=str(MASTER_TENANT),
    )
    def test_delete_by_message_id_tenant_filter(self, _):
        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000010-0000000001', tenant_uuids=[OTHER_TENANT]
        )
        assert_that(result, equal_to(False))

        result = self.dao.voicemail_transcription.delete_by_message_id(
            '0000000010-0000000001', tenant_uuids=[MASTER_TENANT]
        )
        assert_that(result, equal_to(True))
