# -*- coding: utf-8 -*-

# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
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

import unittest

from kombu import Queue, Exchange
from hamcrest import assert_that, equal_to
from mock import Mock

from ..bus_client import BusClient, _CELConsumer
from ..manager import CallLogsManager


class TestCelConsumer(unittest.TestCase):

    def setUp(self):
        self.body = {'data': {'EventName': 'LINKEDID_END',
                              'LinkedID': 'a-linked-id'}}
        self.consumer = _CELConsumer(Mock(Queue))
        self.consumer._call_logs_manager = Mock(CallLogsManager)

    def test_that_message_is_acked(self):
        message = Mock()

        self.consumer.on_message(self.body, message)

        message.ack.assert_called_once_with()

    def test_that_the_manager_is_called(self):
        self.consumer.on_message(self.body, Mock())

        self.consumer._call_logs_manager.generate_from_linked_id.assert_called_once_with('a-linked-id')


class TestBusClient(unittest.TestCase):

    def setUp(self):
        self._config = {
            'bus': {
                'exchange_name': 'my_exchange',
                'exchange_type': 'topic',
                'username': 'u1',
                'password': 'secret',
                'host': 'localhost',
                'port': 1234,
            }
        }
        self.expected_bus_url = 'amqp://u1:secret@localhost:1234//'
        self.expected_exchange = Exchange('my_exchange', type='topic')
        self.bus_client = BusClient(self._config)

    def test_that_the_queue_is_created(self):
        expected_queue = Queue(exchange=self.expected_exchange,
                               routing_key=BusClient._KEY,
                               exclusive=True)

        assert_that(self.bus_client.queue, equal_to(expected_queue))

    def test_the_bus_url(self):
        assert_that(self.bus_client.bus_url, equal_to(self.expected_bus_url))
