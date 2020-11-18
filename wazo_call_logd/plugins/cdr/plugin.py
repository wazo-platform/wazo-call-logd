# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_auth_client import Client as AuthClient

from .resource import CDRResource
from .resource import CDRIdResource
from .resource import CDRUserResource
from .resource import CDRUserMeResource
from .service import CDRService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        dao = dependencies['dao']

        auth_client = AuthClient(**config['auth'])
        service = CDRService(dao.call_log)

        api.add_resource(CDRResource, '/cdr', resource_class_args=[service])
        api.add_resource(
            CDRIdResource, '/cdr/<int:cdr_id>', resource_class_args=[service]
        )
        api.add_resource(
            CDRUserResource,
            '/users/<uuid:user_uuid>/cdr',
            resource_class_args=[service],
        )
        api.add_resource(
            CDRUserMeResource,
            '/users/me/cdr',
            resource_class_args=[auth_client, service],
        )
