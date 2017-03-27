# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from .resource import CDRResource
from .service import CDRService


class Plugin(object):

    def load(self, dependencies):
        api = dependencies['api']
        service = CDRService()

        api.add_resource(CDRResource, '/cdr', resource_class_args=[service])
