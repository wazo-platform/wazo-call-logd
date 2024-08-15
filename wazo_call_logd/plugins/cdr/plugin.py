# Copyright 2017-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_auth_client import Client as AuthClient

from wazo_call_logd.plugins.export.notifier import ExportNotifier

from .http import (
    CDRIdResource,
    CDRResource,
    CDRUserMeResource,
    CDRUserResource,
    RecordingMediaItemResource,
    RecordingMediaItemUserMeResource,
    RecordingsMediaExportResource,
    RecordingsMediaResource,
)
from .services import CDRService, RecordingService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        dao = dependencies['dao']
        bus_publisher = dependencies['bus_publisher']
        export_notifier = ExportNotifier(bus_publisher)

        auth_client = AuthClient(**config['auth'])
        cdr_service = CDRService(dao)
        recording_service = RecordingService(dao, config, export_notifier)

        api.add_resource(
            CDRResource,
            '/cdr',
            resource_class_args=[cdr_service],
        )
        api.add_resource(
            RecordingsMediaResource,
            '/cdr/recordings/media',
            resource_class_args=[recording_service, cdr_service],
        )
        api.add_resource(
            RecordingsMediaExportResource,
            '/cdr/recordings/media/export',
            resource_class_args=[recording_service, cdr_service, api],
        )
        api.add_resource(
            CDRIdResource,
            '/cdr/<int:cdr_id>',
            resource_class_args=[cdr_service],
        )
        api.add_resource(
            RecordingMediaItemResource,
            '/cdr/<int:cdr_id>/recordings/<uuid:recording_uuid>/media',
            resource_class_args=[recording_service, cdr_service],
        )
        api.add_resource(
            CDRUserResource,
            '/users/<uuid:user_uuid>/cdr',
            resource_class_args=[cdr_service],
        )
        api.add_resource(
            CDRUserMeResource,
            '/users/me/cdr',
            resource_class_args=[auth_client, cdr_service],
        )
        api.add_resource(
            RecordingMediaItemUserMeResource,
            '/users/me/cdr/<int:cdr_id>/recordings/<uuid:recording_uuid>/media',
            resource_class_args=[recording_service, cdr_service, auth_client],
        )
