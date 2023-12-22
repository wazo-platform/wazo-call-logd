# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging

from wazo_auth_client import Client as AuthClient
from xivo import xivo_logging
from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo_dao import init_db_from_config

from wazo_call_logd.config import DEFAULT_CONFIG, _load_key_file
from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.models import Tenant
from wazo_call_logd.database.queries.tenant import TenantDAO
from wazo_call_logd.purger import CallLogsPurger, ExportsPurger, RecordingsPurger

logger = logging.getLogger('wazo-call-logd-sync-db')


def parse_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help="Log debug messages",
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help='Only print warnings and errors',
    )
    parsed_args = parser.parse_args()
    result = {'log_level': logging.INFO}
    if parsed_args.quiet:
        result['log_level'] = logging.WARNING
    elif parsed_args.debug:
        result['log_level'] = logging.DEBUG
    return result


def load_config():
    file_config = read_config_file_hierarchy(ChainMap(DEFAULT_CONFIG))
    service_key = _load_key_file(ChainMap(file_config, DEFAULT_CONFIG))
    return ChainMap(service_key, file_config, DEFAULT_CONFIG)


def main():
    cli_args = parse_cli_args()
    config = load_config()

    xivo_logging.setup_logging('/dev/null', log_level=cli_args['log_level'])
    xivo_logging.silence_loggers(['stevedore.extension'], logging.WARNING)

    token = AuthClient(**config['auth']).token.new(expiration=300)['token']

    del config['auth']['username']
    del config['auth']['password']
    tenants = AuthClient(token=token, **config['auth']).tenants.list()['items']
    auth_tenants = {str(tenant['uuid']) for tenant in tenants}
    logger.debug('wazo-auth tenants: %s', auth_tenants)

    init_db_from_config(config)
    db_session = new_db_session(config['db_uri'])
    tenant_dao = TenantDAO(db_session)

    with tenant_dao.new_session() as session:
        call_logd_tenants = set()
        for tenant in session.query(Tenant).all():
            call_logd_tenants.add(str(tenant.uuid))
        logger.debug('wazo-call-logd tenants: %s', call_logd_tenants)
        logger.debug('wazo-auth tenants: %s', auth_tenants)

        removed_tenants = call_logd_tenants - auth_tenants
        for tenant_uuid in removed_tenants:
            remove_tenant(tenant_uuid, session)


def remove_tenant(tenant_uuid, session):
    logger.debug('Removing tenant and its related data: %s', tenant_uuid)
    for purger in [CallLogsPurger(), ExportsPurger(), RecordingsPurger()]:
        purger.purge(0, session, tenant_uuid)

    session.query(Tenant).filter(Tenant.uuid == tenant_uuid).delete()


if __name__ == '__main__':
    main()
