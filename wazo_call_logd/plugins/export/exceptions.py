# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class ExportNotFoundException(APIException):
    def __init__(self, export_uuid):
        super().__init__(
            status_code=404,
            message='No export found matching this UUID',
            error_id='export-not-found-with-given-uuid',
            details={'export_uuid': str(export_uuid)},
        )


class ExportFSNotFoundException(APIException):
    def __init__(self, export_uuid, export_path):
        super().__init__(
            status_code=500,
            message='Export: not found on filesystem',
            error_id='export-filesystem-not-found',
            details={
                'export_uuid': str(export_uuid),
                'export_path': export_path,
            },
        )


class ExportFSPermissionException(APIException):
    def __init__(self, export_uuid, export_path):
        super().__init__(
            status_code=500,
            message='Export: permission denied',
            error_id='export-permission-denied',
            details={
                'export_uuid': str(export_uuid),
                'export_path': export_path,
            },
        )


class ExportNotDoneYetException(APIException):
    def __init__(self, export_uuid):
        super().__init__(
            status_code=202,
            message='Export: not done yet',
            error_id='export-not-done-yet',
            details={
                'export_uuid': str(export_uuid),
            },
        )
