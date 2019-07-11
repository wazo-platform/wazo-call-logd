# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from threading import Thread
from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo import plugin_helpers
from xivo.status import StatusAggregator, TokenStatus
from xivo.token_renewer import TokenRenewer

from wazo_call_logd.bus_client import BusClient
from wazo_call_logd.cel_fetcher import CELFetcher
from wazo_call_logd.cel_interpretor import DispatchCELInterpretor
from wazo_call_logd.cel_interpretor import CallerCELInterpretor
from wazo_call_logd.cel_interpretor import CalleeCELInterpretor
from wazo_call_logd.cel_interpretor import LocalOriginateCELInterpretor
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.manager import CallLogsManager
from wazo_call_logd.writer import CallLogsWriter
from .bus_publisher import BusPublisher
from .rest_api import api, CoreRestApi

logger = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, config):
        auth_client = AuthClient(**config['auth'])
        cel_fetcher = CELFetcher()
        confd_client = ConfdClient(**config['confd'])
        generator = CallLogsGenerator([
            LocalOriginateCELInterpretor(confd_client),
            DispatchCELInterpretor(CallerCELInterpretor(confd_client),
                                   CalleeCELInterpretor(confd_client))
        ])
        writer = CallLogsWriter()
        self._publisher = BusPublisher(config)
        self.manager = CallLogsManager(cel_fetcher, generator, writer, self._publisher)
        self.bus_client = BusClient(config)
        self.rest_api = CoreRestApi(config)
        self.token_renewer = TokenRenewer(auth_client)
        self.token_renewer.subscribe_to_token_change(
            lambda token: confd_client.set_token(token['token'])
        )
        self.status_aggregator = StatusAggregator()
        self.token_status = TokenStatus()
        plugin_helpers.load(
            namespace='wazo_call_logd.plugins',
            names=config['enabled_plugins'],
            dependencies={
                'api': api,
                'config': config,
                'status_aggregator': self.status_aggregator,
            }
        )

    def run(self):
        logger.info('Starting wazo-call-logd')
        self.token_renewer.subscribe_to_token_change(self.token_status.token_change_callback)
        self.status_aggregator.add_provider(self.bus_client.provide_status)
        self.status_aggregator.add_provider(self.token_status.provide_status)
        bus_publisher_thread = Thread(target=self._publisher.run)
        bus_publisher_thread.start()
        bus_consumer_thread = Thread(target=self.bus_client.run, args=[self.manager], name='bus_consumer_thread')
        bus_consumer_thread.start()

        try:
            with self.token_renewer:
                self.rest_api.run()
        finally:
            logger.info('Stopping wazo-call-logd')
            self.bus_client.stop()
            self._publisher.stop()
            bus_consumer_thread.join()
            bus_publisher_thread.join()

    def stop(self, reason):
        logger.warning('Stopping wazo-call-logd: %s', reason)
        self.rest_api.stop()
