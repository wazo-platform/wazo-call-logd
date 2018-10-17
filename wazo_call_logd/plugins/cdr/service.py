# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

logger = logging.getLogger(__name__)


class CDRService(object):
    def __init__(self, dao):
        self._dao = dao

    def list(self, search_params):
        logger.critical('FIND_ALL CALL')
        call_logs = self._dao.find_all_in_period(search_params)
        logger.critical('COUNT CALL')
        count = self._dao.count_in_period(search_params)
        logger.critical('SERVICE RETURNING')
        return {'items': call_logs,
                'filtered': count['filtered'],
                'total': count['total']}

    def get(self, cdr_id):
        return self._dao.get_by_id(cdr_id)
