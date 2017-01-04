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
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter

_DEFAULT_CONFIG = {
    'logfile': '/var/log/xivo-call-logd.log',
    'pidfile': '/var/run/xivo-call-logd/xivo-call-logd.pid',
    'config_file': '/etc/xivo-call-logd/config.yml',
    'extra_config_files': '/etc/xivo-call-logd/conf.d',
    'foreground': False,
    'debug': False,
    'user': 'xivo-call-logs',
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

    user = config.get('user')
    if user:
        change_user(user)

    xivo_dao.init_db_from_config(config)

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
    parser.add_argument('-c', '--config-file', action='store', help='The path to the config file')
    parser.add_argument('-f', '--foreground', action='store_true',
                        help='run in foreground')
    parser.add_argument('-u', '--user', help='User to run the daemon', default=_DEFAULT_CONFIG['user'])
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase verbosity')
    parsed_args = parser.parse_args()
    if parsed_args.config_file:
        config['config_file'] = parsed_args.config_file
    if parsed_args.foreground:
        config['foreground'] = parsed_args.foreground
    if parsed_args.verbose:
        config['debug'] = parsed_args.verbose
    if parsed_args.user:
        config['user'] = parsed_args.user

    return config


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
    main()
