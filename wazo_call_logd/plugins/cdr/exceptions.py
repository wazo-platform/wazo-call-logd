# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class CDRNotFoundException(APIException):
    def __init__(self, details=None):
        super().__init__(
            status_code=404,
            message='No CDR found matching this ID',
            error_id='cdr-not-found-with-given-id',
            details=details,
        )


class RecordingNotFoundException(APIException):
    def __init__(self, recording_uuid):
        super().__init__(
            status_code=404,
            message='No recording found',
            error_id='recording-not-found',
            details={'recording_uuid': str(recording_uuid)},
        )


class RecordingMediaNotFoundException(APIException):
    def __init__(self, recording_uuid):
        super().__init__(
            status_code=400,
            message='No recording media found',
            error_id='recording-media-not-found',
            details={'recording_uuid': str(recording_uuid)},
        )


class RecordingMediaFSNotFoundException(APIException):
    def __init__(self, recording_uuid, recording_path):
        super().__init__(
            status_code=500,
            message='Recording media: not found on filesystem',
            error_id='recording-media-filesystem-not-found',
            details={
                'recording_uuid': str(recording_uuid),
                'recording_path': recording_path,
            },
        )


class NoRecordingToExportException(APIException):
    def __init__(self):
        super().__init__(
            status_code=400,
            message='No recording to export',
            error_id='no-recording-to-export',
        )


class RecordingMediaFSPermissionException(APIException):
    def __init__(self, recording_uuid, recording_path):
        super().__init__(
            status_code=500,
            message='Recording media: permission denied',
            error_id='recording-media-permission-denied',
            details={
                'recording_uuid': str(recording_uuid),
                'recording_path': recording_path,
            },
        )


class CDRRecordingMediaFSPermissionException(APIException):
    def __init__(self, cdr_id, recording_uuid, recording_path):
        super().__init__(
            status_code=500,
            message='Recording media: permission denied',
            error_id='recording-media-permission-denied',
            details={
                'cdr_id': cdr_id,
                'recording_uuid': str(recording_uuid),
                'recording_path': recording_path,
            },
        )
