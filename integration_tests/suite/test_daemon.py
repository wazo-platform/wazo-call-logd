# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that
from hamcrest import equal_to
from xivo_test_helpers import until

from .test_api.base import IntegrationTest


class TestNoRabbitMQ(IntegrationTest):

    asset = 'no_rabbitmq'

    def test_given_no_rabbitmq_when_stop_then_stopped(self):
        self.stop_service('call-logd')

        def call_logs_is_stopped():
            assert_that(self.service_status('call-logd'), equal_to('Stopped'))

        until.assert_(call_logs_is_stopped, tries=5, interval=1, message='xivo-call-logd did not stop')
