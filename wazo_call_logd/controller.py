# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal

from functools import partial
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
from .database.queries import DAO
from .database.helpers import new_db_session
from .http_server import api, HTTPServer

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config):
        auth_client = AuthClient(**config['auth'])
        cel_fetcher = CELFetcher()
        confd_client = ConfdClient(**config['confd'])
        generator = CallLogsGenerator(
            confd_client,
            [
                LocalOriginateCELInterpretor(confd_client),
                DispatchCELInterpretor(
                    CallerCELInterpretor(confd_client),
                    CalleeCELInterpretor(confd_client),
                ),
            ],
        )
        DBSession = new_db_session(config['db_uri'])
        CELDBSession = new_db_session(config['cel_db_uri'])
        dao = DAO(DBSession, CELDBSession)
        writer = CallLogsWriter(dao)
        self.token_renewer = TokenRenewer(auth_client)
        self.token_renewer.subscribe_to_token_change(confd_client.set_token)
        self.token_renewer.subscribe_to_next_token_details_change(
            generator.set_default_tenant_uuid
        )
        self._publisher = BusPublisher(config)
        self.manager = CallLogsManager(
            dao, cel_fetcher, generator, writer, self._publisher
        )
        self.bus_client = BusClient(config)
        self.http_server = HTTPServer(config)
        self.status_aggregator = StatusAggregator()
        self.token_status = TokenStatus()
        plugin_helpers.load(
            namespace='wazo_call_logd.plugins',
            names=config['enabled_plugins'],
            dependencies={
                'api': api,
                'config': config,
                'dao': dao,
                'token_renewer': self.token_renewer,
                'status_aggregator': self.status_aggregator,
            },
        )

    def run(self):
        logger.info('Starting wazo-call-logd')
        self.token_renewer.subscribe_to_token_change(
            self.token_status.token_change_callback
        )
        self.status_aggregator.add_provider(self.bus_client.provide_status)
        self.status_aggregator.add_provider(self.token_status.provide_status)
        signal.signal(signal.SIGTERM, partial(_sigterm_handler, self))
        bus_publisher_thread = Thread(target=self._publisher.run)
        bus_publisher_thread.start()
        bus_consumer_thread = Thread(
            target=self.bus_client.run, args=[self.manager], name='bus_consumer_thread'
        )
        bus_consumer_thread.start()

        try:
            with self.token_renewer:
                self.http_server.run()
        finally:
            logger.info('Stopping wazo-call-logd')
            self.bus_client.stop()
            self._publisher.stop()
            bus_consumer_thread.join()
            bus_publisher_thread.join()

    def stop(self, reason):
        logger.warning('Stopping wazo-call-logd: %s', reason)
        self.http_server.stop()


def _sigterm_handler(controller, signum, frame):
    controller.stop(reason='SIGTERM')
