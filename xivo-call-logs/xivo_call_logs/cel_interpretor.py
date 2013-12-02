# -*- coding: utf-8 -*-

# Copyright (C) 2013 Avencall
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

from itertools import groupby

from xivo_call_logs import raw_call_log
from xivo_dao.data_handler.cel.event_type import CELEventType


class CallerCELInterpretor(object):
    def interpret_cels(self, caller_cels, call_log):
        for cel in caller_cels:
            call_log = self.interpret_cel(cel, call_log)
        return call_log

    def interpret_cel(self, cel, call):
        eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.app_start: self.interpret_app_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start,
            CELEventType.hangup: self.interpret_hangup,
        }

        eventtype = cel.eventtype
        if eventtype in eventtype_map:
            interpret_function = eventtype_map[eventtype]
            return interpret_function(cel, call)
        else:
            return call

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_exten = cel.cid_num
        call.destination_exten = cel.exten if cel.exten != 's' else ''

        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_name
        call.communication_start = cel.eventtime
        call.answered = True

        return call

    def interpret_bridge_start(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = cel.cid_num

        return call

    def interpret_hangup(self, cel, call):
        call.communication_end = cel.eventtime

        return call


class CalleeCELInterpretor(object):
    pass


class CELInterpretor(object):

    def __init__(self, caller_cel_interpretor, callee_cel_interpretor):
        self.caller_cel_interpretor = caller_cel_interpretor
        self.callee_cel_interpretor = callee_cel_interpretor

    def interpret_call(self, cels):
        raw_call = self.interpret_cels(cels)
        return raw_call.to_call_log()

    def interpret_cels(self, cels):
        call_log = raw_call_log.RawCallLog()
        call_log.cel_ids = [cel.id for cel in cels]

        caller_cels, _ = self.split_caller_callee_cels(cels)
        self.caller_cel_interpretor.interpret_cels(caller_cels, call_log)

        return call_log

    def split_caller_callee_cels(self, cels):
        key_function = lambda cel: cel.uniqueid
        sorted_cels = sorted(cels, key=key_function)
        cels_by_uniqueid = [list(cels) for _, cels in groupby(sorted_cels, key=key_function)]

        caller_cels = cels_by_uniqueid[0] if len(cels_by_uniqueid) > 0 else []
        callee_cels = cels_by_uniqueid[1] if len(cels_by_uniqueid) > 1 else []
        return (caller_cels, callee_cels)
