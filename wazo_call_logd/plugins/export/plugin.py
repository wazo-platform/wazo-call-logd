# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .services import ExportService

from .http import (
    ExportDownloadResource,
    ExportResource,
)


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        dao = dependencies['dao']

        export_service = ExportService(dao)

        api.add_resource(
            ExportResource,
            '/exports/<uuid:export_uuid>',
            resource_class_args=[export_service],
            endpoint='export_resource',
        )

        api.add_resource(
            ExportDownloadResource,
            '/exports/<uuid:export_uuid>/download',
            resource_class_args=[export_service],
            endpoint='export_download_resource',
        )
