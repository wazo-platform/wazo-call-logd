# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class DatabaseServiceUnavailable(Exception):
    def __init__(self):
        super().__init__('Postgresql is unavailable')


class TokenWithUserUUIDRequiredError(APIException):
    def __init__(self):
        super().__init__(
            status_code=400,
            message='A valid token with a user UUID is required',
            error_id='token-with-user-uuid-required',
        )


class InvalidCallLogException(ValueError):
    pass


class ExportNotFoundException(APIException):
    def __init__(self, export_uuid):
        super().__init__(
            status_code=404,
            message='No export found matching this UUID',
            error_id='export-not-found-with-given-uuid',
            details={'export_uuid': str(export_uuid)},
        )
