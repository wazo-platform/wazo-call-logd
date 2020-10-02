# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class QueueNotFoundException(APIException):
    def __init__(self, details=None):
        super(QueueNotFoundException, self).__init__(
            status_code=404,
            message='No queue found matching this ID',
            error_id='queue-not-found-with-given-id',
            details=details,
        )
