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

import datetime

from xivo_dao.resources.call_log.model import CallLog

from xivo_call_logs.exceptions import InvalidCallLogException


class RawCallLog(object):

    def __init__(self):
        self.date = None
        self.source_name = None
        self.source_exten = None
        self.destination_name = None
        self.destination_exten = None
        self.user_field = None
        self.answered = False
        self.communication_start = None
        self.communication_end = None
        self.source_line_identity = None
        self.destination_line_identity = None
        self.participants = []

    def to_call_log(self):
        if not self.date:
            raise InvalidCallLogException('date not found')
        if not (self.source_name or self.source_exten):
            raise InvalidCallLogException('source name and exten not found')

        result = CallLog(
            date=self.date,
            date_answer=self.communication_start,
            source_name=self.source_name,
            source_exten=self.source_exten,
            destination_name=self.destination_name,
            destination_exten=self.destination_exten,
            user_field=self.user_field,
            answered=self.answered,
            duration=self.duration,
            source_line_identity=self.source_line_identity,
            destination_line_identity=self.destination_line_identity,
        )
        result.set_participants(self.participants)
        result.add_related_cels(self.cel_ids)

        return result

    @property
    def duration(self):
        default_value = datetime.timedelta(0)
        communication_start = getattr(self, 'communication_start')
        communication_end = getattr(self, 'communication_end')
        if communication_start and communication_end:
            duration = communication_end - communication_start
            return max(duration, default_value)
        else:
            return default_value
