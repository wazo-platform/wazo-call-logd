# Copyright 2012-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging
import sys
from datetime import date

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo.chain_map import ChainMap
from xivo.config_helper import (
    parse_config_file,
    read_config_file_hierarchy,
    set_xivo_uuid,
)
from xivo.daemonize import pidfile_context
from xivo.token_renewer import TokenRenewer
from xivo.xivo_logging import setup_logging, silence_loggers
from xivo_dao import init_db_from_config

from wazo_call_logd.bus import BusPublisher
from wazo_call_logd.cel_interpretor import default_interpretors
from wazo_call_logd.config import DEFAULT_CONFIG
from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO
from wazo_call_logd.generator import CallLogsGenerator
from wazo_call_logd.manager import CallLogsManager
from wazo_call_logd.writer import CallLogsWriter

DEFAULT_CEL_COUNT = 20000
PIDFILENAME = '/run/wazo-call-logs.pid'

logger = logging.getLogger(__name__)


def main():
    _print_deprecation_notice()
    parser = argparse.ArgumentParser(description='Call logs generator')
    options = parse_args(parser)
    setup_logging('/dev/null', debug=options.debug)
    silence_loggers(['urllib3.connectionpool'], level=logging.WARNING)
    with pidfile_context(PIDFILENAME):
        _generate_call_logs(options)


def _print_deprecation_notice():
    if sys.argv[0].endswith('xivo-call-logs'):
        print(
            'Warning: xivo-call-logs is a deprecated alias to wazo-call-logs:'
            ' use wazo-call-logs instead'
        )


def _generate_call_logs(cli_options: argparse.Namespace):
    file_config = {
        key: value
        for key, value in read_config_file_hierarchy(DEFAULT_CONFIG).items()
        if key in ('confd', 'bus', 'auth', 'db_uri', 'cel_db_uri')
    }

    key_config = {}
    auth_username = file_config['auth'].get('username')
    auth_password = file_config['auth'].get('password')
    if not (auth_username and auth_password):
        key_config = load_key_file(ChainMap(file_config, DEFAULT_CONFIG))

    config = ChainMap(key_config, file_config, DEFAULT_CONFIG)
    logger.debug('Config: %s', config)

    set_xivo_uuid(config, logger)
    logger.debug('CEL database is %s', config['cel_db_uri'])
    init_db_from_config({'db_uri': config['cel_db_uri']})
    logger.debug('call-logd database is %s', config['db_uri'])
    DBSession = new_db_session(config['db_uri'])
    CELDBSession = new_db_session(config['cel_db_uri'])
    dao = DAO(DBSession, CELDBSession)

    auth_client = AuthClient(**config['auth'])
    confd_client = ConfdClient(**config['confd'])
    token_renewer = TokenRenewer(auth_client)
    token_renewer.subscribe_to_token_change(confd_client.set_token)

    generator = CallLogsGenerator(
        confd_client,
        default_interpretors(),
    )
    token_renewer.subscribe_to_next_token_details_change(
        generator.set_default_tenant_uuid
    )
    writer = CallLogsWriter(dao)
    publisher = BusPublisher(service_uuid=config['uuid'], **config['bus'])
    manager = CallLogsManager(dao, generator, writer, publisher)

    options = vars(cli_options)
    with token_renewer:
        if options.get('action') == 'delete':
            if options.get('all'):
                manager.delete_all()
            elif options.get('days'):
                manager.delete_from_days(options['days'])
        else:
            if options.get('days'):
                manager.generate_from_days(days=options['days'])
            elif start_date := options.get('start-date'):
                parsed_start_date = date.fromisoformat(start_date)
                if end_date := options.get('end-date'):
                    parsed_end_date = date.fromisoformat(end_date)
                else:
                    parsed_end_date = date.today()
                manager.generate_from_dates(parsed_start_date, parsed_end_date)
            else:
                manager.generate_from_count(cel_count=options['cel_count'])


def parse_args(parser: argparse.ArgumentParser):
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
    generate_date_range_group = parser.add_argument_group('Date range')
    generate_date_range_group.add_argument(
        '-s', '--start-date', type=str, help='Start date'
    )
    generate_date_range_group.add_argument(
        '-e', '--end-date', type=str, help='End date', required=False
    )
    parser.add_argument(
        '-D',
        '--debug',
        action='store_true',
        dest='debug',
        default=False,
        help='Enable debug logging',
    )
    return parser.parse_args()


def load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }
