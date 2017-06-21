# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from datetime import datetime, timedelta

from xivo_dao.helpers.db_utils import session_scope
from xivo_dao.resources.call_log import dao as call_log_dao

logger = logging.getLogger(__name__)


class CallLogsManager(object):

    def __init__(self, cel_fetcher, generator, writer, publisher):
        self.cel_fetcher = cel_fetcher
        self.generator = generator
        self.writer = writer
        self.publisher = publisher

    def delete_all(self):
        with session_scope():
            call_log_dao.delete()

    def delete_from_days(self, days):
        older = datetime.now() - timedelta(days=days)
        with session_scope():
            call_log_dao.delete(older=older)

    def generate_from_days(self, days):
        older_cel = datetime.now() - timedelta(days=days)
        with session_scope():
            cels = self.cel_fetcher.fetch_last_unprocessed(older=older_cel)
            self._generate_from_cels(cels)

    def generate_from_count(self, cel_count):
        with session_scope():
            cels = self.cel_fetcher.fetch_last_unprocessed(cel_count)
            logger.debug('Generating call logs from the last %s CEL (found %s)', cel_count, len(cels))
            self._generate_from_cels(cels)

    def generate_from_linked_id(self, linked_id):
        with session_scope():
            cels = self.cel_fetcher.fetch_from_linked_id(linked_id)
            logger.debug('Generating call log for linked_id %s from %s CEL', linked_id, len(cels))
            self._generate_from_cels(cels)

    def _generate_from_cels(self, cels):
        call_logs = self.generator.from_cel(cels)
        logger.debug('Generated %s call logs', len(call_logs.new_call_logs))
        self.writer.write(call_logs)
        self.publisher.publish_all(call_logs.new_call_logs)
