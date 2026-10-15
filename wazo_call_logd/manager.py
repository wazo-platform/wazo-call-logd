# Copyright 2013-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .database.queries import DAO

logger = logging.getLogger(__name__)


class CallLogsManager:
    def __init__(self, dao, generator, writer, publisher):
        self.dao: DAO = dao
        self.generator = generator
        self.writer = writer
        self.publisher = publisher

    def delete_all(self):
        self.dao.call_log.delete()
        self.dao.cel.unassociate_all()

    def delete_from_days(self, days):
        older = datetime.now() - timedelta(days=days)
        deleted_call_log_ids = self.dao.call_log.delete(older=older)
        self.dao.cel.unassociate_all_from_call_log_ids(deleted_call_log_ids)

    def generate_from_days(self, days):
        older_cel = datetime.now() - timedelta(days=days)
        cels = self.dao.cel.find_last_unprocessed(older=older_cel)
        self._generate_from_cels(cels)

    def generate_from_dates(self, start_date, end_date):
        cels = self.dao.cel.find_unprocessed(start_date=start_date, end_date=end_date)
        self._generate_from_cels(cels)

    def generate_from_count(self, cel_count):
        cels = self.dao.cel.find_last_unprocessed(cel_count)
        logger.debug(
            'Generating call logs from the last %s CEL (found %s)',
            cel_count,
            len(cels),
        )
        self._generate_from_cels(cels)

    def generate_from_linked_id(self, linked_id):
        cels = self.dao.cel.find_from_linked_id(linked_id)
        logger.debug(
            'Generating call log for linked_id %s from %s CEL', linked_id, len(cels)
        )
        self._generate_from_cels(cels)

    def _generate_from_cels(self, cels):
        call_logs = self.generator.from_cel(cels)
        logger.debug('Generated %s call logs', len(call_logs.new_call_logs))
        self.writer.write(call_logs)
        self.publisher.publish_call_log(*call_logs.new_call_logs)
