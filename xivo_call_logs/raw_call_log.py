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

from xivo_dao.alchemy.call_log import CallLog

from xivo_call_logs.exceptions import InvalidCallLogException


class RawCallLog(object):

    def __init__(self):
        self.date = None
        self.date_end = None
        self.source_name = None
        self.source_exten = None
        self.destination_name = None
        self.destination_exten = None
        self.user_field = None
        self.date_answer = None
        self.source_line_identity = None
        self.destination_line_identity = None
        self.direction = 'internal'
        self.participants = []
        self.cel_ids = []

    def to_call_log(self):
        if not self.date:
            raise InvalidCallLogException('date not found')
        if not (self.source_name or self.source_exten):
            raise InvalidCallLogException('source name and exten not found')

        result = CallLog(
            date=self.date,
            date_answer=self.date_answer,
            date_end=self.date_end,
            source_name=self.source_name,
            source_exten=self.source_exten,
            destination_name=self.destination_name,
            destination_exten=self.destination_exten,
            user_field=self.user_field,
            source_line_identity=self.source_line_identity,
            destination_line_identity=self.destination_line_identity,
            direction=self.direction,
        )
        result.participants = self.participants
        result.cel_ids = self.cel_ids

        return result
