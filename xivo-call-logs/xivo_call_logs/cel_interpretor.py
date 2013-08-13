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

from xivo_dao.data_handler.call_log import model
from xivo_dao.data_handler.cel.event_type import CELEventType


class CELInterpretor(object):

    def interpret_call(self, cels):
        filtered_cels = self.filter_cels(cels)
        return self.interpret_cels(filtered_cels)

    def filter_cels(self, cels):
        if not cels:
            return []

        first_unique_id = cels[0].uniqueid
        return [cel for cel in cels if cel.uniqueid == first_unique_id]

    def interpret_cels(self, cels):
        call_log = model.CallLog()
        for cel in cels:
            call_log = self.interpret_cel(cel, call_log)

        return call_log

    def interpret_cel(self, cel, call):
        eventtype_map = {
            CELEventType.chan_start: self.interpret_chan_start,
            CELEventType.answer: self.interpret_answer,
            CELEventType.bridge_start: self.interpret_bridge_start,
            CELEventType.hangup: self.interpret_hangup,
            CELEventType.chan_end: self.interpret_chan_end,
        }

        eventtype = cel.eventtype
        if eventtype in eventtype_map:
            interpret_function = eventtype_map[eventtype]
            return interpret_function(cel, call)
        elif eventtype not in CELEventType.eventtype_list:
            return self.interpret_unknown(cel, call)

    def interpret_chan_start(self, cel, call):
        call.date = cel.eventtime
        call.source_name = cel.cid_name
        call.source_exten = cel.cid_num
        call.destination_exten = cel.exten
        call.user_field = cel.userfield

        return call

    def interpret_answer(self, cel, call):
        if not call.destination_exten:
            call.destination_exten = cel.cid_name

        return call

    def interpret_bridge_start(self, cel, call):
        if not call.source_name:
            call.source_name = cel.cid_name
        if not call.source_exten:
            call.source_exten = cel.cid_num

        return call

    def interpret_hangup(self, cel, call):
        raise NotImplementedError()

    def interpret_chan_end(self, cel, call):
        raise NotImplementedError()

    def interpret_unknown(self, cel, call):
        pass
