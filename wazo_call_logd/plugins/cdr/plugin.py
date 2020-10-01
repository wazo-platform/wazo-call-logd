# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_auth_client import Client as AuthClient

from wazo_call_logd.database.helpers import new_db_session
from wazo_call_logd.database.queries import DAO

from .resource import CDRResource
from .resource import CDRIdResource
from .resource import CDRUserResource
from .resource import CDRUserMeResource
from .service import CDRService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']

        auth_client = AuthClient(**config['auth'])
        dao = DAO(new_db_session(config['db_uri'])).call_log
        service = CDRService(dao)

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
