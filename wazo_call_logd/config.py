# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import os

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file, read_config_file_hierarchy
from xivo.xivo_logging import get_log_level_by_name

_PID_DIR = '/run/wazo-call-logd'

DEFAULT_CONFIG = {
    'logfile': '/var/log/wazo-call-logd.log',
    'log_level': 'info',
    'config_file': '/etc/wazo-call-logd/config.yml',
    'extra_config_files': '/etc/wazo-call-logd/conf.d',
    'debug': False,
    'user': 'wazo-call-logd',
    'db_upgrade_on_startup': False,
    'db_uri': (
        'postgresql://asterisk:proformatique@localhost/asterisk?'
        'application_name=wazo-call-logd'
    ),
    'cel_db_uri': (
        'postgresql://asterisk:proformatique@localhost/asterisk?'
        'application_name=wazo-call-logd'
    ),
    'email_export_body_template': '/var/lib/wazo-call-logd/templates/email_export_body.j2',
    'email_export_token_expiration': 48 * 3600,  # 48 hours
    'email_export_from_name': 'Wazo',
    'email_export_from_address': 'no-reply@wazo.community',
    'email_export_subject': 'Your export is ready',
    'exports': {
        'directory': '/var/lib/wazo-call-logd/exports',
        'key_file': '/var/lib/wazo-auth-keys/wazo-call-logd-export-key.yml',
    },
    'bus': {
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': '5672',
        'exchange_name': 'wazo-headers',
        'exchange_type': 'headers',
    },
    'celery': {
        'broker': 'amqp://guest:guest@localhost:5672',
        'exchange_name': 'celery-call-logd',
        'queue_name': 'celery-call-logd',
        'worker_pid_file': os.path.join(_PID_DIR, 'celery-worker.pid'),
        'worker_min': 3,
        'worker_max': 5,
    },
    'enabled_celery_tasks': {
        'recording_export': True,
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
        'max_threads': 10,
    },
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-call-logd-key.yml',
        'master_tenant_uuid': None,
    },
    'confd': {'host': 'localhost', 'port': 9486, 'prefix': None, 'https': False},
    'enabled_plugins': {
        'api': True,
        'cdr': True,
        'config': True,
        'export': True,
        'retention': True,
        'status': True,
        'support_center': True,
    },
    'smtp': {
        'host': 'localhost',
        'port': 25,
        'starttls': True,
        'timeout': 10,
        'username': None,
        'password': None,
    },
    'retention': {
        'cdr_days': None,
        'export_days': None,
        'recording_days': None,
    },
}


def load(argv):
    cli_config = _parse_cli_args(argv)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, DEFAULT_CONFIG))
    reinterpreted_config = _get_reinterpreted_raw_values(
        ChainMap(cli_config, file_config, DEFAULT_CONFIG)
    )
    service_key = _load_key_file(ChainMap(cli_config, file_config, DEFAULT_CONFIG))
    return ChainMap(
        reinterpreted_config, cli_config, service_key, file_config, DEFAULT_CONFIG
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
    updated_config = {}
    export_id = config['exports'].get('service_id')
    export_key = config['exports'].get('service_key')
    if not (export_id and export_key):
        export_key_file = parse_config_file(config['exports']['key_file'])
        if export_key_file:
            updated_config.update(
                {
                    'exports': {
                        'service_id': export_key_file['service_id'],
                        'service_key': export_key_file['service_key'],
                    }
                }
            )

    auth_username = config['auth'].get('username')
    auth_password = config['auth'].get('password')
    if not (auth_username and auth_password):
        key_file = parse_config_file(config['auth']['key_file'])
        if key_file:
            updated_config.update(
                {
                    'auth': {
                        'username': key_file['service_id'],
                        'password': key_file['service_key'],
                    }
                }
            )
    return updated_config


def _get_reinterpreted_raw_values(config):
    result = {}

    log_level = config.get('log_level')
    if log_level:
        result['log_level'] = get_log_level_by_name(log_level)

    return result
