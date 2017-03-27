# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dao.resources.call_log import dao


class CDRService(object):
    def list(self):
        return dao.find_all()
