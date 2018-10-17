# -*- coding: utf-8 -*-
# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_entry,
)
from xivo_test_helpers import until

from .helpers.base import IntegrationTest


class TestStatusNoRabbitMQ(IntegrationTest):

    asset = 'no_rabbitmq'

    def test_given_no_rabbitmq_when_status_then_rabbitmq_fail(self):
        result = self.call_logd.status.get()

        assert_that(result['bus_consumer']['status'], equal_to('fail'))


class TestStatusRabbitMQStops(IntegrationTest):

    asset = 'base'

    def setUp(self):
        self.bus = self.make_bus()
        until.true(self.bus.is_up, timeout=10)

    def test_given_rabbitmq_stops_when_status_then_rabbitmq_fail(self):
        self.stop_service('rabbitmq')

        def rabbitmq_is_down():
            result = self.call_logd.status.get()
            assert_that(result['bus_consumer']['status'], equal_to('fail'))

        until.assert_(rabbitmq_is_down, timeout=5)


class TestStatusAllOK(IntegrationTest):

    asset = 'base'

    def setUp(self):
        self.bus = self.make_bus()
        until.true(self.bus.is_up, timeout=10)

    def test_given_auth_and_ari_and_rabbitmq_when_status_then_status_ok(self):

        def all_ok():
            result = self.call_logd.status.get()
            assert_that(result, has_entries(
                bus_consumer=has_entry('status', 'ok'),
                service_token=has_entry('status', 'ok'),
            ))

        until.assert_(all_ok, tries=10)
