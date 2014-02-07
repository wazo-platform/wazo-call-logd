# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
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

from collections import namedtuple
from itertools import groupby
from xivo_call_logs.exceptions import InvalidCallLogException


CallLogsCreation = namedtuple('CallLogsCreation', ('new_call_logs', 'call_logs_to_delete'))


class CallLogsGenerator(object):

    def __init__(self, cel_interpretor):
        self.cel_interpretor = cel_interpretor

    def from_cel(self, cels):
        call_logs_to_delete = self.list_call_log_ids(cels)
        new_call_logs = self.call_logs_from_cel(cels)
        return CallLogsCreation(new_call_logs=new_call_logs, call_logs_to_delete=call_logs_to_delete)

    def call_logs_from_cel(self, cels):
        result = []
        for linkedid, cels_by_call_iter in self._group_cels_by_linkedid(cels):
            cels_by_call = list(cels_by_call_iter)
            try:
                call = self.cel_interpretor.interpret_call(cels_by_call)
                result.append(call)
            except InvalidCallLogException:
                pass

        return result

    def list_call_log_ids(self, cels):
        return set(cel.call_log_id for cel in cels if cel.call_log_id)

    def _group_cels_by_linkedid(self, cels):
        key_function = lambda cel: cel.linkedid
        cels = sorted(cels, key=key_function)
        return groupby(cels, key=key_function)
