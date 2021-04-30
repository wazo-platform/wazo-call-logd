# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_auth_client import Client as AuthClient

from .services import build_service

from .http import (
    ExportResource,
)


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        dao = dependencies['dao']

        auth_client = AuthClient(**config['auth'])
        export_service = build_service(dao)

        api.add_resource(
            ExportResource,
            '/exports/<uuid:export_uuid>',
            resource_class_args=[export_service],
            endpoint='export_resource',
        )
