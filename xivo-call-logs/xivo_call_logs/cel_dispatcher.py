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

from xivo_call_logs import raw_call_log
from xivo_dao.data_handler.cel.event_type import CELEventType


class CELDispatcher(object):

    def __init__(self, caller_cel_interpretor, callee_cel_interpretor):
        self.caller_cel_interpretor = caller_cel_interpretor
        self.callee_cel_interpretor = callee_cel_interpretor

    def interpret_call(self, cels):
        raw_call = self.interpret_cels(cels)
        return raw_call.to_call_log()

    def interpret_cels(self, cels):
        call_log = raw_call_log.RawCallLog()
        call_log.cel_ids = [cel.id for cel in cels]

        caller_cels, callee_cels = self.split_caller_callee_cels(cels)
        call_log = self.caller_cel_interpretor.interpret_cels(caller_cels, call_log)
        call_log = self.callee_cel_interpretor.interpret_cels(callee_cels, call_log)

        return call_log

    def split_caller_callee_cels(self, cels):
        uniqueids = [cel.uniqueid for cel in cels if cel.eventtype == CELEventType.chan_start]
        caller_uniqueid = uniqueids[0] if len(uniqueids) > 0 else None
        callee_uniqueid = uniqueids[1] if len(uniqueids) > 1 else None

        caller_cels = [cel for cel in cels if cel.uniqueid == caller_uniqueid]
        callee_cels = [cel for cel in cels if cel.uniqueid == callee_uniqueid]

        return (caller_cels, callee_cels)
