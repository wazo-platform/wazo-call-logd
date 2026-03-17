# Copyright 2017-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from uuid import UUID

from wazo_test_helpers.bus import BusClient


class CallLogBusClient(BusClient):
    def send_linkedid_end(self, linkedid):
        payload = {
            'data': {
                'EventName': 'LINKEDID_END',
                'LinkedID': linkedid,
            },
            'name': 'CEL',
        }
        self.publish(payload, headers={'name': 'CEL'})

    def send_tenant_deleted(self, tenant_uuid: str | UUID):
        payload = {'data': {'uuid': str(tenant_uuid)}, 'name': 'auth_tenant_deleted'}
        self.publish(payload, headers={'name': 'auth_tenant_deleted'})

    def send_voicemail_transcription_completed(self, event_data: dict):
        payload = {
            'data': event_data,
            'name': 'voicemail_transcription_completed',
        }
        self.publish(payload, headers={'name': 'voicemail_transcription_completed'})

    def send_voicemail_message_deleted(
        self, message_id: str, event_name: str = 'user_voicemail_message_deleted'
    ):
        payload = {
            'data': {'message_id': message_id},
            'name': event_name,
        }
        self.publish(payload, headers={'name': event_name})
