# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from threading import Thread

from xivo_call_logs.bus_client import BusClient
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.cel_interpretor import LocalOriginateCELInterpretor
from xivo_call_logs.core import plugin_manager
from xivo_call_logs.core.rest_api import api, CoreRestApi
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter

logger = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, config):
        cel_fetcher = CELFetcher()
        generator = CallLogsGenerator([
            LocalOriginateCELInterpretor,
            DispatchCELInterpretor(CallerCELInterpretor(),
                                   CalleeCELInterpretor())
        ])
        writer = CallLogsWriter()
        self.manager = CallLogsManager(cel_fetcher, generator, writer)
        self.bus_client = BusClient(config)
        self.rest_api = CoreRestApi(config)
        self._load_plugins(config)

    def run(self):
        logger.info('Starting xivo-call-logd')
        bus_consumer_thread = Thread(target=self.bus_client.run, args=[self.manager], name='bus_consumer_thread')
        bus_consumer_thread.start()

        try:
            self.rest_api.run()
        finally:
            logger.info('Stopping xivo-call-logd')
            self.bus_client.stop()
            bus_consumer_thread.join()

    def stop(self, reason):
        logger.warning('Stopping xivo-call-logd: %s', reason)
        raise SystemExit()

    def _load_plugins(self, global_config):
        load_args = [{
            'api': api,
            'config': global_config,
        }]
        plugin_manager.load_plugins(global_config['enabled_plugins'], load_args)
