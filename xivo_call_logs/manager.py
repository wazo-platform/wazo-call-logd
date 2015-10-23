# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Avencall
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

from xivo_dao.helpers.db_utils import session_scope


class CallLogsManager(object):

    def __init__(self, cel_fetcher, generator, writer):
        self.cel_fetcher = cel_fetcher
        self.generator = generator
        self.writer = writer

    def generate_from_count(self, cel_count):
        with session_scope():
            cels = self.cel_fetcher.fetch_last_unprocessed(cel_count)
            self._generate_from_cels(cels)

    def generate_from_linked_id(self, linked_id):
        with session_scope():
            cels = self.cel_fetcher.fetch_from_linked_id(linked_id)
            self._generate_from_cels(cels)

    def _generate_from_cels(self, cels):
        call_logs = self.generator.from_cel(cels)
        self.writer.write(call_logs)
