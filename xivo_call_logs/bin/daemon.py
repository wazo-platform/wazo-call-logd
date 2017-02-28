# -*- coding: utf-8 -*-

# Copyright (C) 2012-2017 The Wazo Authors  (see the AUTHORS file)
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

import argparse
import logging
import signal
import sys
import xivo_dao

from xivo.daemonize import pidfile_context
from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging
from xivo_call_logs.bus_client import BusClient
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.cel_interpretor import LocalOriginateCELInterpretor
from xivo_call_logs.config import load as load_config
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter

logger = logging.getLogger(__name__)


def main(argv):
    config = load_config(argv)

    user = config.get('user')
    if user:
        change_user(user)

    setup_logging(config['logfile'], config['foreground'], config['debug'], config['log_level'])
    xivo_dao.init_db_from_config(config)

    with pidfile_context(config['pidfile'], config['foreground']):
        logger.info('Starting xivo-call-logd')
        try:
            _run(config)
        except Exception:
            logger.exception('Unexpected error:')
        finally:
            logger.info('Stopping xivo-call-logd')


def _run(config):
    _init_signal()

    cel_fetcher = CELFetcher()
    generator = CallLogsGenerator([
        LocalOriginateCELInterpretor,
        DispatchCELInterpretor(CallerCELInterpretor(),
                               CalleeCELInterpretor())
    ])
    writer = CallLogsWriter()
    manager = CallLogsManager(cel_fetcher, generator, writer)
    bus_client = BusClient(config)

    bus_client.run(manager)


def _init_signal():
    signal.signal(signal.SIGTERM, _handle_sigterm)


def _handle_sigterm(signum, frame):
    del signum
    del frame
    raise SystemExit()


if __name__ == '__main__':
    main(sys.argv[1:])
