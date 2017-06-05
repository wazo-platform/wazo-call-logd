# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from .resources import SwaggerResource


class Plugin(object):

    def load(self, dependencies):
        api = dependencies['api']
        api.add_resource(SwaggerResource, '/api/api.yml')
