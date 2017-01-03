# -*- coding: utf-8 -*-

# Copyright (C) 2013-2017 The Wazo Authors  (see the AUTHORS file)
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

from xivo.asterisk.line_identity import identity_from_channel
from xivo_dao.resources.cel.event_type import CELEventType


class DispatchCELInterpretor(object):

    def __init__(self, caller_cel_interpretor, callee_cel_interpretor):
        self.caller_cel_interpretor = caller_cel_interpretor
        self.callee_cel_interpretor = callee_cel_interpretor

    def interpret_cels(self, cels, call_log):
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

    def can_interpret(self):
        return True


class AbstractCELInterpretor(object):

    eventtype_map = {}

    def interpret_cels(self, cels, call_log):
        for cel in cels:
            call_log = self.interpret_cel(cel, call_log)
        return call_log

    def interpret_cel(self, cel, call):
        eventtype = cel.eventtype
        if eventtype in self.eventtype_map:
            interpret_function = self.eventtype_map[eventtype]
            return interpret_function(cel, call)
        else:
            return call


class CallerCELInterpretor(AbstractCELInterpretor):

    def __init__(self):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.app_start: self.interpret_app_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_end: self.interpret_bridge_end_or_exit,
            CELEventType.bridge_enter: self.interpret_bridge_start_or_enter,
            CELEventType.bridge_exit: self.interpret_bridge_end_or_exit,
            CELEventType.xivo_from_s: self.interpret_xivo_from_s,
        }

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_exten = cel.cid_num
        call.destination_exten = cel.exten if cel.exten != 's' else ''
        call.source_line_identity = identity_from_channel(cel.channame)

        return call

    def interpret_app_start(self, cel, call):
        call.user_field = cel.userfield
        if cel.cid_name != '' and cel.cid_num != '':
            call.source_name = cel.cid_name
            call.source_exten = cel.cid_num

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_name

        return call

    def interpret_bridge_start_or_enter(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = cel.cid_num

        call.communication_start = cel.eventtime
        call.answered = True

        return call

    def interpret_bridge_end_or_exit(self, cel, call):
        call.communication_end = cel.eventtime

        return call

    def interpret_xivo_from_s(self, cel, call):
        call.destination_exten = cel.exten

        return call


class CalleeCELInterpretor(AbstractCELInterpretor):
    def __init__(self):
        self.eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
        }

    def interpret_chan_start(self, cel, call):
        call.destination_line_identity = identity_from_channel(cel.channame)

        return call
