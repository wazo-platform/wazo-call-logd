# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_call_logs.core.database.dao import new_db_session
from xivo_call_logs.core.database.dao import CallLogDAO

from .resource import CDRResource
from .service import CDRService


class Plugin(object):

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']

        dao = CallLogDAO(new_db_session(config['db_uri']))
        service = CDRService(dao)

        api.add_resource(CDRResource, '/cdr', resource_class_args=[service])
