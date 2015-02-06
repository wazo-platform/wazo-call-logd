# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
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

from kombu import Exchange, Connection, Queue
from kombu.mixins import ConsumerMixin


class _CELConsumer(ConsumerMixin):

    def __init__(self, connection, queue, call_logs_manager):
        self.connection = connection
        self._queue = queue
        self._call_logs_manager = call_logs_manager

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(self._queue, callbacks=[self.on_message]),
        ]

    def on_message(self, body, message):
        msg = json.loads(body)
        if msg['data']['EventName'] == 'LINKEDID_END':
            self._call_logs_manager.generate_from_linked_id(msg['data']['LinkedID'])

        message.ack()


class BusClient(object):

    _KEY = 'ami.CEL'

    def __init__(self, config):
        self.bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(**config['bus'])
        exchange = Exchange(config['bus']['exchange_name'],
                            type=config['bus']['exchange_type'])
        self.queue = Queue(exchange=exchange, routing_key=self._KEY, exclusive=True)

    def run(self, call_logs_manager):
        with Connection(self.bus_url) as conn:
            consumer = _CELConsumer(conn, self.queue, call_logs_manager)
            consumer.run()
