# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+


class CDRService(object):
    def __init__(self, dao):
        self._dao = dao

    def list(self, from_, until, order, direction, limit, offset, search, user_uuid):
        call_logs = self._dao.find_all_in_period(from_, until, order, direction, limit, offset, search, user_uuid)
        count = self._dao.count_in_period(from_, until, search, user_uuid)
        return {'items': map(CDR.from_call_log, call_logs),
                'filtered': count['filtered'],
                'total': count['total']}


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
