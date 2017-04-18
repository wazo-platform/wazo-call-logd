# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dao.resources.call_log import dao


class CDRService(object):
    def list(self, from_, until, order, direction, limit, offset):
        order = 'date' if order == 'start' else order
        return [CDR.from_call_log(call_log) for call_log in dao.find_all_in_period(from_, until, order, direction, limit, offset)]


class CDR(object):

    @classmethod
    def from_call_log(cls, call_log):
        result = cls()
        for attribute in ('answered',
                          'date',
                          'destination_exten',
                          'destination_name',
                          'duration',
                          'source_exten',
                          'source_name'):
            setattr(result, attribute, getattr(call_log, attribute))

        result.end = call_log.date + call_log.duration

        return result
