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
        raise NotImplementedError()
