# Copyright 2012-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging
import sys

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file
from xivo.config_helper import read_config_file_hierarchy
from xivo.daemonize import pidfile_context
from xivo.token_renewer import TokenRenewer
from xivo.xivo_logging import setup_logging
from xivo.xivo_logging import silence_loggers
from xivo_dao import init_db_from_config, default_config

from wazo_call_logd.bus_publisher import BusPublisher
from wazo_call_logd.cel_fetcher import CELFetcher
from wazo_call_logd.cel_interpretor import DispatchCELInterpretor
from wazo_call_logd.cel_interpretor import CallerCELInterpretor
from wazo_call_logd.cel_interpretor import CalleeCELInterpretor
from wazo_call_logd.cel_interpretor import LocalOriginateCELInterpretor
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.manager import CallLogsManager
from wazo_call_logd.writer import CallLogsWriter

DEFAULT_CEL_COUNT = 20000
PIDFILENAME = '/var/run/wazo-call-logs.pid'

_CERT_FILE = '/usr/share/xivo-certs/server.crt'
DEFAULT_CONFIG = {
    'pidfile': PIDFILENAME,
    'config_file': '/etc/wazo-call-logd/config.yml',
    'extra_config_files': '/etc/wazo-call-logd/conf.d',
    'db_uri': 'postgresql://asterisk:proformatique@localhost/asterisk',
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'timeout': 2,
        'verify_certificate': _CERT_FILE,
        'key_file': '/var/lib/wazo-auth-keys/wazo-call-logd-key.yml',
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
    'confd': {'host': 'localhost', 'port': 9486, 'verify_certificate': _CERT_FILE},
}


def main():
    _print_deprecation_notice()
    setup_logging('/dev/null', foreground=True, debug=False)
    silence_loggers(['urllib3.connectionpool'], level=logging.WARNING)
    init_db_from_config(default_config())
    with pidfile_context(PIDFILENAME, foreground=True):
        _generate_call_logs()


def _print_deprecation_notice():
    if sys.argv[0].endswith('xivo-call-logs'):
        print(
            'Warning: xivo-call-logs is a deprecated alias to wazo-call-logs: use wazo-call-logs instead'
        )


def _generate_call_logs():
    parser = argparse.ArgumentParser(description='Call logs generator')
    options = parse_args(parser)

    file_config = {
        key: value
        for key, value in read_config_file_hierarchy(DEFAULT_CONFIG).items()
        if key in ('confd', 'bus', 'auth', 'db_uri')
    }
    key_config = load_key_file(ChainMap(file_config, DEFAULT_CONFIG))
    config = ChainMap(key_config, file_config, DEFAULT_CONFIG)

    auth_client = AuthClient(**config['auth'])
    confd_client = ConfdClient(**config['confd'])
    token_renewer = TokenRenewer(auth_client)
    token_renewer.subscribe_to_token_change(confd_client.set_token)

    cel_fetcher = CELFetcher()
    generator = CallLogsGenerator(
        confd_client,
        [
            LocalOriginateCELInterpretor(confd_client),
            DispatchCELInterpretor(
                CallerCELInterpretor(confd_client), CalleeCELInterpretor(confd_client)
            ),
        ],
    )
    token_renewer.subscribe_to_next_token_details_change(
        generator.set_default_tenant_uuid
    )
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
    group_action.add_argument(
        'action', nargs='?', choices=['delete', 'generate'], default='generate'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-A',
        '--all',
        action='store_true',
        help='Delete all call logs. Can only be used with argument delete',
    )
    group.add_argument(
        '-c',
        '--cel-count',
        default=DEFAULT_CEL_COUNT,
        type=int,
        help='Minimum number of CEL entries to process',
    )
    group.add_argument('-d', '--days', type=int, help='Number of days to process')
    return parser.parse_args()


def load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }
