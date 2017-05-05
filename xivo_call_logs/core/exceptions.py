# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.rest_api_helpers import APIException


class DatabaseServiceUnavailable(Exception):

    def __init__(self):
        super(DatabaseServiceUnavailable, self).__init__('Postgresql is unavailable')


class TokenWithUserUUIDRequiredError(APIException):

    def __init__(self):
        super(TokenWithUserUUIDRequiredError, self).__init__(
            status_code=400,
            message='A valid token with a user UUID is required',
            error_id='token-with-user-uuid-required',
        )
