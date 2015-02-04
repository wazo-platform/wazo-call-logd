# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 Avencall
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


class CallLogsOrchestrator(object):

    def __init__(self, bus_client, call_logs_manager):
        self._bus_client = bus_client
        self._call_logs_manager = call_logs_manager

    def run(self):
        self._bus_client.run(self._call_logs_manager)
