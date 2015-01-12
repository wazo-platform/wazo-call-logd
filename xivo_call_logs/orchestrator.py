# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 Avencall
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

import logging
import time
from xivo_bus.ctl.consumer import BusConsumerError

logger = logging.getLogger(__name__)


class CallLogsOrchestrator(object):

    _KEY = 'ami.CEL'
    _RECONNECTION_DELAY = 5
    _QUEUE_NAME = 'xivo-call-logd-queue'

    def __init__(self, bus_consumer, call_logs_manager, config):
        self.bus_consumer = bus_consumer
        self.call_logs_manager = call_logs_manager
        self._config = config

    def run(self):
        while True:
            try:
                self._start_consuming_bus_events()
            except BusConsumerError:
                self._handle_bus_connection_error()
            except Exception:
                self._handle_unexpected_error()

    def _start_consuming_bus_events(self):
        self.bus_consumer.connect()
        self.bus_consumer.add_binding(self.on_cel_event,
                                      self._QUEUE_NAME,
                                      self._config['bus']['exchange_name'],
                                      self._KEY)
        self.bus_consumer.run()

    def _handle_bus_connection_error(self):
        logger.warning('Bus connection error')
        self.bus_consumer.stop()
        time.sleep(self._RECONNECTION_DELAY)

    def _handle_unexpected_error(self):
        logger.exception('Unexpected error')
        self.bus_consumer.stop()
        raise

    def on_cel_event(self, body):
        if body['data']['EventName'] == 'LINKEDID_END':
            linked_id = body['data']['LinkedID']
            self.call_logs_manager.generate_from_linked_id(linked_id)
