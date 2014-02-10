# -*- coding: utf-8 -*-

# Copyright (C) 2012-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import json
import logging
import time
from xivo_bus.ctl.consumer import BusConnectionError

logger = logging.getLogger(__name__)


class CallLogsOrchestrator(object):

    _EXCHANGE = 'xivo-ami'
    _KEY = 'cel'
    _RECONNECTION_DELAY = 5

    def __init__(self, bus_consumer, call_logs_manager):
        self.bus_consumer = bus_consumer
        self.call_logs_manager = call_logs_manager

    def run(self):
        while True:
            try:
                self._start_consuming_bus_events()
            except BusConnectionError as e:
                self._handle_bus_connection_error(e)
            except Exception as e:
                self._handle_unexpected_error(e)

    def _start_consuming_bus_events(self):
            self.bus_consumer.add_listner(self._EXCHANGE, self._KEY, self.on_cel_event)
            self.bus_consumer.run()

    def _handle_bus_connection_error(self, e):
            logger.exception(e)
            self.bus_consumer.stop()
            time.sleep(self._RECONNECTION_DELAY)

    def _handle_unexpected_error(self, e):
            logger.exception(e)
            self.bus_consumer.stop()
            raise e

    def on_cel_event(self, channel, method, header, body):
        body = json.loads(body)
        if body['name'] == 'CEL' and body['data']['EventName'] == 'LINKEDID_END':
            linked_id = body['data']['LinkedID']
            self.call_logs_manager.generate_from_linked_id(linked_id)
        channel.basic_ack(delivery_tag=method.delivery_tag)
