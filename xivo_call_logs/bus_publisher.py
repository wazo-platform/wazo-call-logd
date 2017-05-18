# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from functools import partial

import kombu
import xivo_bus
from marshmallow import pre_dump
from xivo_bus.resources.call_logs.events import CallLogCreatedEvent, CallLogUserCreatedEvent
from xivo_call_logs.plugins.cdr.schema import CDRSchema

logger = logging.getLogger(__name__)


class ModelCDRSchema(CDRSchema):

    @pre_dump
    def _populate_tags_field(self, data):
        data.tags = set()
        for participant in data.get_participants():
            data.tags.update(participant.tags)
        return data


class BusPublisher(object):

    def __init__(self, config):
        uuid = config.get('uuid')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(**config['bus'])
        exchange_name = config['bus']['exchange_name']
        exchange_type = config['bus']['exchange_type']
        publisher_fcty = partial(self._new_publisher, uuid, bus_url, exchange_name, exchange_type)
        self._publisher = xivo_bus.PublishingQueue(publisher_fcty)

    def publish_all(self, call_logs):
        for call_log in call_logs:
            self.publish(call_log)

    def publish(self, call_log):
        payload = ModelCDRSchema().dump(call_log).data
        logger.debug('publishing new call log: %s', payload)
        event = CallLogCreatedEvent(payload)
        self.send_event(event)

        payload = ModelCDRSchema(exclude=['tags']).dump(call_log).data
        for participant in call_log.get_participants():
            event = CallLogUserCreatedEvent(participant.user_uuid, payload)
            self.send_event(event)

    def run(self):
        logger.info('status publisher starting')
        self._publisher.run()

    def stop(self):
        logger.info('status publisher stoping')
        self._publisher.stop()

    def _new_publisher(self, uuid, url, exchange_name, exchange_type):
        bus_connection = kombu.Connection(url)
        bus_exchange = kombu.Exchange(exchange_name, type=exchange_type)
        bus_producer = kombu.Producer(bus_connection, exchange=bus_exchange, auto_declare=True)
        bus_marshaler = xivo_bus.Marshaler(uuid)
        return xivo_bus.Publisher(bus_producer, bus_marshaler)

    def send_event(self, event):
        self._publisher.publish(event)
