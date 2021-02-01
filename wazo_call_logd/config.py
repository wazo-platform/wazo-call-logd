# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file
from xivo.config_helper import read_config_file_hierarchy
from xivo.xivo_logging import get_log_level_by_name

_DEFAULT_CONFIG = {
    'logfile': '/var/log/wazo-call-logd.log',
    'log_level': 'info',
    'config_file': '/etc/wazo-call-logd/config.yml',
    'extra_config_files': '/etc/wazo-call-logd/conf.d',
    'debug': False,
    'user': 'wazo-call-logd',
    'db_upgrade_on_startup': False,
    'db_uri': 'postgresql://asterisk:proformatique@localhost/asterisk',
    'cel_db_uri': 'postgresql://asterisk:proformatique@localhost/asterisk',
    'bus': {
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': '5672',
        'exchange_name': 'xivo',
        'exchange_type': 'topic',
        'exchange_durable': True,
    },
    'rest_api': {
        'listen': '127.0.0.1',
        'port': 9298,
        'certificate': None,
        'private_key': None,
        'cors': {
            'enabled': True,
            'allow_headers': ['Content-Type', 'X-Auth-Token', 'Wazo-Tenant'],
        },
    },
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-call-logd-key.yml',
    },
    'confd': {'host': 'localhost', 'port': 9486, 'prefix': None, 'https': False},
    'enabled_plugins': {
        'api': True,
        'cdr': True,
        'support_center': True,
        'status': True,
    },
}


def load(argv):
    cli_config = _parse_cli_args(argv)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    reinterpreted_config = _get_reinterpreted_raw_values(
        ChainMap(cli_config, file_config, _DEFAULT_CONFIG)
    )
    service_key = _load_key_file(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    return ChainMap(
        reinterpreted_config, cli_config, service_key, file_config, _DEFAULT_CONFIG
    )


def _parse_cli_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db-upgrade-on-startup",
        action="store_true",
        default=False,
        help="Upgrade database on startup if needed",
    )
    parser.add_argument(
        '-c',
        '--config-file',
        action='store',
        help="The path where is the config file. Default: %(default)s",
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help="Log debug messages. Overrides log_level. Default: %(default)s",
    )
    parser.add_argument(
        '-l',
        '--log-level',
        action='store',
        help="Logs messages with LOG_LEVEL details. Must be one of:\n"
        "critical, error, warning, info, debug. Default: %(default)s",
    )
    parser.add_argument(
        '-u', '--user', action='store', help="The owner of the process."
    )
    parsed_args = parser.parse_args(argv)

    result = {}
    if parsed_args.db_upgrade_on_startup:
        result['db_upgrade_on_startup'] = parsed_args.db_upgrade_on_startup
    if parsed_args.config_file:
        result['config_file'] = parsed_args.config_file
    if parsed_args.debug:
        result['debug'] = parsed_args.debug
    if parsed_args.log_level:
        result['log_level'] = parsed_args.log_level
    if parsed_args.user:
        result['user'] = parsed_args.user

    return result


def _load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    if not key_file:
        return {}
    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }


def _get_reinterpreted_raw_values(config):
    result = {}

    log_level = config.get('log_level')
    if log_level:
        result['log_level'] = get_log_level_by_name(log_level)

    return result
