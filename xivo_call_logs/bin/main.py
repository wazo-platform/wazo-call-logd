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

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file
from xivo.daemonize import pidfile_context
from xivo.token_renewer import TokenRenewer
from xivo.xivo_logging import setup_logging
from xivo.xivo_logging import silence_loggers
from xivo_auth_client import Client as AuthClient
from xivo_confd_client import Client as ConfdClient
from xivo_dao import init_db_from_config, default_config

from xivo_call_logs.bus_publisher import BusPublisher
from xivo_call_logs.cel_fetcher import CELFetcher
from xivo_call_logs.cel_interpretor import DispatchCELInterpretor
from xivo_call_logs.cel_interpretor import CallerCELInterpretor
from xivo_call_logs.cel_interpretor import CalleeCELInterpretor
from xivo_call_logs.cel_interpretor import LocalOriginateCELInterpretor
from xivo_call_logs.generator import CallLogsGenerator
from xivo_call_logs.manager import CallLogsManager
from xivo_call_logs.writer import CallLogsWriter

DEFAULT_CEL_COUNT = 20000
PIDFILENAME = '/var/run/xivo-call-logs.pid'

_CERT_FILE = '/usr/share/xivo-certs/server.crt'
DEFAULT_CONFIG = {
    'pidfile': '/var/run/xivo-call-logs.pid',
    'db_uri': 'postgresql://asterisk:proformatique@localhost/asterisk',
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'timeout': 2,
        'verify_certificate': _CERT_FILE,
        'key_file': '/var/lib/xivo-auth-keys/xivo-call-logd-key.yml',
    },
    'bus': {
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': '5672',
        'exchange_name': 'xivo',
        'exchange_type': 'topic',
        'exchange_durable': True,
    },
    'confd': {
        'host': 'localhost',
        'port': 9486,
        'verify_certificate': _CERT_FILE,
    },
}


def main():
    setup_logging('/dev/null', foreground=True, debug=False)
    silence_loggers(['urllib3.connectionpool'], level=logging.WARNING)
    init_db_from_config(default_config())
    with pidfile_context(PIDFILENAME, foreground=True):
        _generate_call_logs()


def _generate_call_logs():
    parser = argparse.ArgumentParser(description='Call logs generator')
    options = parse_args(parser)
    key_config = load_key_file(DEFAULT_CONFIG)
    config = ChainMap(key_config, DEFAULT_CONFIG)

    auth_client = AuthClient(**config['auth'])
    confd_client = ConfdClient(**config['confd'])
    token_renewer = TokenRenewer(auth_client)
    token_renewer.subscribe_to_token_change(confd_client.set_token)

    cel_fetcher = CELFetcher()
    generator = CallLogsGenerator([
        LocalOriginateCELInterpretor(confd_client),
        DispatchCELInterpretor(CallerCELInterpretor(confd_client),
                               CalleeCELInterpretor(confd_client))
    ])
    writer = CallLogsWriter()
    publisher = BusPublisher(config)
    manager = CallLogsManager(cel_fetcher, generator, writer, publisher)

    options = vars(options)
    with token_renewer:
        if options.get('action') == 'delete':
            if options.get('all'):
                manager.delete_all()
            elif options.get('days'):
                manager.delete_from_days(options['days'])
        else:
            if options.get('days'):
                manager.generate_from_days(days=options['days'])
            else:
                manager.generate_from_count(cel_count=options['cel_count'])


def parse_args(parser):
    group_action = parser.add_mutually_exclusive_group()
    group_action.add_argument('action', nargs='?', choices=['delete', 'generate'], default='generate')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-A', '--all',
                       action='store_true',
                       help='Delete all call logs. Can only be used with argument delete')
    group.add_argument('-c', '--cel-count',
                       default=DEFAULT_CEL_COUNT,
                       type=int,
                       help='Minimum number of CEL entries to process')
    group.add_argument('-d', '--days',
                       type=int,
                       help='Number of days to process')
    return parser.parse_args()


def load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {'auth': {'username': key_file['service_id'],
                     'password': key_file['service_key']}}
