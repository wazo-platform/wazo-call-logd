# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_auth_client import Client as AuthClient


from .celery_tasks import RecordingExportTask
from .http import (
    CDRResource,
    CDRIdResource,
    CDRUserResource,
    CDRUserMeResource,
    RecordingMediaItemResource,
    RecordingsMediaExportResource,
    RecordingsMediaResource,
)
from .services import CDRService, RecordingService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        dao = dependencies['dao']

        auth_client = AuthClient(**config['auth'])
        cdr_service = CDRService(dao)
        recording_service = RecordingService(dao, config['exports'])

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
            resource_class_args=[recording_service, cdr_service, api, auth_client],
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
