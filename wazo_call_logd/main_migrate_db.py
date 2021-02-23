# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import datetime
import gzip
import io
import logging
import psycopg2
import sys

from wazo_call_logd.config import DEFAULT_CONFIG
from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging
from xivo.xivo_logging import get_log_level_by_name

logger = logging.getLogger(__name__)


def parse_args(parser):
    group_action = parser.add_mutually_exclusive_group()
    group_action.add_argument(
        'action',
        nargs='?',
        choices=['call-log'],
        default='call-log',
    )

    parser.add_argument(
        '-i',
        '--index',
        action='store_true',
        help='Migrate and overwrite call_log index',
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help="Log debug messages. Overrides log_level. Default: %(default)s",
    )
    parser.add_argument(
        '-m',
        '--max-entries',
        nargs='?',
        type=int,
        help='Maximum entries to migrate. If exceed, nothing will be executed and command will return code 1',
    )
    return parser.parse_args()


def main():
    parser = argparse.ArgumentParser(description='Call logs database migrator')
    options = parse_args(parser)

    file_config = {
        key: value
        for key, value in read_config_file_hierarchy(DEFAULT_CONFIG).items()
        if key in ('db_uri', 'cel_db_uri')
    }
    config = ChainMap(file_config, DEFAULT_CONFIG)

    if config['user']:
        change_user(config['user'])

    setup_logging(
        config['logfile'],
        debug=config['debug'] or options.debug,
        log_level=get_log_level_by_name(config['log_level']),
    )
    options = vars(options)
    if options.get('action') == 'call-log':
        if options.get('index'):
            migrate_call_log_index(config)
        else:
            migrate_call_log_tables(config, options.get('max_entries'))


def migrate_call_log_index(config):
    with psycopg2.connect(config['cel_db_uri']) as cel_conn:
        with psycopg2.connect(config['db_uri']) as conn:
            cel_cur = cel_conn.cursor()
            cur = conn.cursor()
            if not table_exists(cel_cur, 'call_log'):
                logger.info('Migration already done')
                sys.exit(2)

            logger.info('Migrate call log index...')
            query = 'SELECT last_value FROM call_log_id_seq;'
            cel_cur.execute(query)
            last_old_call_log_id = cel_cur.fetchone()[0]
            query = f"SELECT setval('call_logd_call_log_id_seq', {last_old_call_log_id}, true);"
            cur.execute(query)
            logger.info('Call log index migrated')


def migrate_call_log_tables(config, max_entries):
    with psycopg2.connect(config['cel_db_uri']) as cel_conn:
        with psycopg2.connect(config['db_uri']) as conn:
            cel_cur = cel_conn.cursor()
            cur = conn.cursor()

            if (
                not table_exists(cel_cur, 'call_log')
                or not table_exists(cel_cur, 'call_log_participant')
            ):
                logger.info('Migration already done')
                sys.exit(2)

            query = 'SELECT count(*) FROM call_log;'
            cel_cur.execute(query)
            count_call_log = cel_cur.fetchone()[0]
            logger.debug('call_log: %s entries to migrate', count_call_log)
            query = 'SELECT count(*) FROM call_log_participant;'
            cel_cur.execute(query)
            count_call_log_participant = cel_cur.fetchone()[0]
            logger.debug('call_log_participant: %s entries to migrate', count_call_log_participant)
            total_rows = count_call_log + count_call_log_participant
            if max_entries and total_rows > max_entries:
                logger.error('Too much entries to process. Maximum allowed: %s', max_entries)
                sys.exit(3)

            logger.info('Migrate call log tables. This may take a while...')

            logger.debug('Migrate tenants...')
            query = 'SELECT DISTINCT tenant_uuid FROM call_log;'
            cel_cur.execute(query)
            query = "INSERT INTO call_logd_tenant (uuid) VALUES ('{uuid}') ON CONFLICT DO NOTHING;"
            for row in cel_cur:
                cur.execute(query.format(uuid=row[0]))
            logger.debug('Tenants migrated')

            logger.info('Migrate call_log table...')
            columns = [
                'id',
                'date',
                'date_answer',
                'date_end',
                'tenant_uuid',
                'source_name',
                'source_exten',
                'source_internal_exten',
                'source_internal_context',
                'source_line_identity',
                'requested_name',
                'requested_exten',
                'requested_context',
                'requested_internal_exten',
                'requested_internal_context',
                'destination_name',
                'destination_exten',
                'destination_internal_exten',
                'destination_internal_context',
                'destination_line_identity',
                'direction',
                'user_field',
            ]
            start_time = datetime.datetime.now()
            table_name = 'call_log'
            obj = read_table(cel_cur, table_name, columns)
            table_name = 'call_logd_call_log'
            write_table(cur, obj, table_name, columns)
            end_time = datetime.datetime.now()
            logger.info('call_log table migrated in %s', end_time - start_time)

            logger.info('Migrate call_log_participant table...')
            columns = [
                'uuid',
                'call_log_id',
                'user_uuid',
                'line_id',
                'role',
                'tags',
                'answered',
            ]
            start_time = datetime.datetime.now()
            table_name = 'call_log_participant'
            obj = read_table(cel_cur, table_name, columns)
            table_name = 'call_logd_call_log_participant'
            write_table(cur, obj, table_name, columns)
            end_time = datetime.datetime.now()
            logger.info('call_log_participant table migrated in %s', end_time - start_time)

            logger.info('Verifying everything is ok...')
            query = 'SELECT count(*) FROM call_logd_call_log;'
            cur.execute(query)
            new_count_call_log = cur.fetchone()[0]
            if new_count_call_log < count_call_log:
                logger.error(
                    "call_log: entries to migrate (%s) don't match entries migrated (%s)",
                    count_call_log,
                    new_count_call_log,
                )
                sys.exit(4)
            query = 'SELECT count(*) FROM call_logd_call_log_participant;'
            cur.execute(query)
            new_count_call_log_participant = cur.fetchone()[0]
            if new_count_call_log_participant < count_call_log_participant:
                logger.error(
                    "call_log_participant: entries to migrate (%s) don't match entries migrated (%s)",
                    count_call_log_participant,
                    new_count_call_log_participant,
                )
                sys.exit(4)
            logger.debug(
                'call_log: (%s/%s), call_log_participant: (%s/%s)',
                new_count_call_log,
                count_call_log,
                new_count_call_log_participant,
                count_call_log_participant,
            )

            logger.info('Removing old tables...')
            query = 'DROP TABLE call_log, call_log_participant;'
            cel_cur.execute(query)
            logger.info('Old tables removed')

    logger.info('Call logs tables successfully migrated')


def read_table(cursor, table_name, columns):
    start_time = datetime.datetime.now()
    obj_io = io.BytesIO()
    obj_zip_write = gzip.GzipFile(fileobj=obj_io, mode='w')  # avoid high memory usage
    cursor.copy_to(obj_zip_write, table_name, columns=columns)
    obj_zip_write.close()
    obj_io.seek(0)
    end_time = datetime.datetime.now()
    logger.debug('Extracting %s table in %s', table_name, end_time - start_time)
    return obj_io


def write_table(cursor, obj, table_name, columns):
    start_time = datetime.datetime.now()
    obj_zip_read = gzip.GzipFile(fileobj=obj, mode='r')
    cursor.copy_from(obj_zip_read, table_name, columns=columns)
    obj_zip_read.close()
    end_time = datetime.datetime.now()
    logger.debug('Writing %s table in %s', table_name, end_time - start_time)


def table_exists(cursor, table_name):
    query = f"SELECT to_regclass('{table_name}');"
    cursor.execute(query)
    return cursor.fetchone()[0]
