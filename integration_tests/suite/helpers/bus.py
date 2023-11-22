# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

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
