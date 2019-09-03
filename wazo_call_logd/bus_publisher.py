# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from functools import partial

import kombu
import xivo_bus
from xivo_bus.resources.call_logs.events import (
    CallLogCreatedEvent,
    CallLogUserCreatedEvent,
)
from wazo_call_logd.plugins.cdr.schema import CDRSchema

logger = logging.getLogger(__name__)


class BusPublisher(object):
    def __init__(self, config):
        uuid = config.get('uuid')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(**config['bus'])
        exchange_name = config['bus']['exchange_name']
        exchange_type = config['bus']['exchange_type']
        publisher_fcty = partial(
            self._new_publisher, uuid, bus_url, exchange_name, exchange_type
        )
        self._publisher = xivo_bus.PublishingQueue(publisher_fcty)

    def publish_all(self, call_logs):
        for call_log in call_logs:
            self.publish(call_log)

    def publish(self, call_log):
        payload = CDRSchema().dump(call_log)
        logger.debug('publishing new call log: %s', payload)
        event = CallLogCreatedEvent(payload)
        self._publisher.publish(event)

        payload = CDRSchema(exclude=['tags']).dump(call_log)
        for participant in call_log.participants:
            event = CallLogUserCreatedEvent(participant.user_uuid, payload)
            self._publisher.publish(
                event,
                headers={'user_uuid:{uuid}'.format(uuid=participant.user_uuid): True},
            )

    def run(self):
        logger.info('status publisher starting')
        self._publisher.run()

    def stop(self):
        logger.info('status publisher stoping')
        self._publisher.stop()

    def _new_publisher(self, uuid, url, exchange_name, exchange_type):
        bus_connection = kombu.Connection(url)
        bus_exchange = kombu.Exchange(exchange_name, type=exchange_type)
        bus_producer = kombu.Producer(
            bus_connection, exchange=bus_exchange, auto_declare=True
        )
        bus_marshaler = xivo_bus.Marshaler(uuid)
        return xivo_bus.Publisher(bus_producer, bus_marshaler)
