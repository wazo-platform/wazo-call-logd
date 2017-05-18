# -*- coding: utf-8 -*-
# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
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

import logging

from xivo_dao.helpers.db_utils import session_scope

logger = logging.getLogger(__name__)


class CallLogsManager(object):

    def __init__(self, cel_fetcher, generator, writer, publisher):
        self.cel_fetcher = cel_fetcher
        self.generator = generator
        self.writer = writer
        self.publisher = publisher

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
