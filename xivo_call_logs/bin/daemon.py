# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 Avencall
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

from xivo.daemonize import pidfile_context
from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo.xivo_logging import setup_logging
from xivo_bus.ctl.consumer import BusConsumer
from xivo_bus.ctl.config import BusConfig
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_dispatcher import CELDispatcher
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.orchestrator import CallLogsOrchestrator
from xivo_call_logs.writer import CallLogsWriter

_DEFAULT_CONFIG = {
    'logfile': '/var/log/xivo-call-logd.log',
    'pidfile': '/var/run/xivo-call-logd.pid',
    'config_file': '/etc/xivo-call-logd/config.yml',
    'extra_config_files': '/etc/xivo-call-logd/conf.d',
    'foreground': False,
    'debug': False,
    'bus': {
        'exchange_name': 'xivo',
        'exchange_type': 'topic',
        'exchange_durable': True,
    },
}

logger = logging.getLogger(__name__)


def main():
    cli_config = _parse_args()
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    config = ChainMap(cli_config, file_config, _DEFAULT_CONFIG)

    setup_logging(config['logfile'], config['foreground'], config['debug'])

    with pidfile_context(config['pidfile'], config['foreground']):
        logger.info('Starting xivo-call-logd')
        try:
            _run(config)
        except Exception:
            logger.exception('Unexpected error:')
        finally:
            logger.info('Stopping xivo-call-logd')


def _parse_args():
    config = {}
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground', action='store_true',
                        help='run in foreground')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase verbosity')
    parsed_args = parser.parse_args()
    if parsed_args.foreground:
        config['foreground'] = parsed_args.foreground
    if parsed_args.verbose:
        config['debug'] = parsed_args.verbose

    return config


def _run(config):
    _init_signal()
    orchestrator = _init_orchestrator(config)
    orchestrator.run()


def _init_signal():
    signal.signal(signal.SIGTERM, _handle_sigterm)


def _handle_sigterm(signum, frame):
    raise SystemExit()


def _init_orchestrator(config):
    bus_consumer = BusConsumer(BusConfig(**config['bus']))
    cel_fetcher = CELFetcher()
    caller_cel_interpretor = CallerCELInterpretor()
    callee_cel_interpretor = CalleeCELInterpretor()
    cel_dispatcher = CELDispatcher(caller_cel_interpretor,
                                   callee_cel_interpretor)
    generator = CallLogsGenerator(cel_dispatcher)
    writer = CallLogsWriter()
    manager = CallLogsManager(cel_fetcher, generator, writer)
    return CallLogsOrchestrator(bus_consumer, manager, config)


if __name__ == '__main__':
    main()
