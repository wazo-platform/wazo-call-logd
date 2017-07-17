# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+


class CDRService(object):
    def __init__(self, dao):
        self._dao = dao

    def list(self, search_params):
        call_logs = self._dao.find_all_in_period(search_params)
        count = self._dao.count_in_period(search_params)
        return {'items': call_logs,
                'filtered': count['filtered'],
                'total': count['total']}

    def get(self, cdr_id):
        return self._dao.get_by_id(cdr_id)
