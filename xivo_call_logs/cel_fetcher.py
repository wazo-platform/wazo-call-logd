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

from xivo_dao.resources.cel import dao as cel_dao


class CELFetcher(object):

    def fetch_last_unprocessed(self, cel_count=None, older=None):
        return cel_dao.find_last_unprocessed(cel_count, older)

    def fetch_from_linked_id(self, linked_id):
        return cel_dao.find_from_linked_id(linked_id)
