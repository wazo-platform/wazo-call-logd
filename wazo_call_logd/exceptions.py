# Copyright 2013-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Sequence

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


class CELInterpretationError(Exception):
    def __init__(self, event_name: str, raw_data=None):
        super().__init__(
            f'Failed to interpret event {event_name}.'
            + ('' if not raw_data else f' payload: {repr(raw_data)}')
        )
        self.event_name = event_name
        self.raw_data = raw_data


class CELInterpretorError(Exception):
    """
    Generic error raised when a CEL interpretor fails to interpret a CEL sequence
    """

    def __init__(
        self, msg: str | None = None, linkedids: Sequence[int] | None = None
    ) -> None:
        super().__init__(
            msg
            or 'Unexpected CEL sequence'
            + ('' if not linkedids else f' for linkedids {linkedids}')
        )
        self.linkedids = linkedids and tuple(linkedids)
