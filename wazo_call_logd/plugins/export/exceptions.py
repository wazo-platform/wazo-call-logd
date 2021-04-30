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
