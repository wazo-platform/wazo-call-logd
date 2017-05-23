# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+


class CDRService(object):
    def __init__(self, dao):
        self._dao = dao

    def list(self, from_, until, order, direction, limit, offset, search, call_direction, user_uuid):
        call_logs = self._dao.find_all_in_period(from_, until, order, direction, limit, offset, search,
                                                 call_direction, user_uuid)
        count = self._dao.count_in_period(from_, until, search, call_direction, user_uuid)
        return {'items': call_logs,
                'filtered': count['filtered'],
                'total': count['total']}
