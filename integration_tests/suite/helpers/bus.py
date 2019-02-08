# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_test_helpers.bus import BusClient


class CallLogBusClient(BusClient):

    def send_linkedid_end(self, linkedid):
        payload = {
            'data': {
                'EventName': 'LINKEDID_END',
                'LinkedID': linkedid,
            }
        }
        self.publish(payload, routing_key='ami.CEL')
