# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dao.alchemy.call_log import CallLog

from wazo_call_logd.exceptions import InvalidCallLogException


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
