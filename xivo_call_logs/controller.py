# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from xivo_call_logs.bus_client import BusClient
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.cel_interpretor import LocalOriginateCELInterpretor
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

    def run(self):
        logger.info('Starting xivo-call-logd')
        try:
            self.bus_client.run(self.manager)
        except Exception:
            logger.exception('Unexpected error:')
        finally:
            logger.info('Stopping xivo-call-logd')

    def stop(self, reason):
        logger.warning('Stopping xivo-call-logd: %s', reason)
        raise SystemExit()
