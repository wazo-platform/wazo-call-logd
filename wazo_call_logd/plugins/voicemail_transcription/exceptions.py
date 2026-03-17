# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class TranscriptionNotFoundException(APIException):
    def __init__(self, message_id):
        super().__init__(
            status_code=404,
            message='No transcription found for this voicemail message',
            error_id='transcription-not-found',
            details={'message_id': str(message_id)},
        )
