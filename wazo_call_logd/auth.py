# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import request
from requests import HTTPError
from werkzeug.local import LocalProxy as Proxy
from xivo import auth_verifier
from xivo.rest_api_helpers import APIException

from .exceptions import TokenWithUserUUIDRequiredError
from .http_server import app

logger = logging.getLogger(__name__)
required_acl = auth_verifier.required_acl
extract_token_id_from_query_or_header = (
    auth_verifier.extract_token_id_from_query_or_header
)


class _NotInitializedException(APIException):
    def __init__(self):
        msg = 'wazo-call-logd is not initialized'
        super().__init__(503, msg, 'not-initialized')


def init_master_tenant(token):
    tenant_uuid = token['metadata']['tenant_uuid']
    app.config['auth']['master_tenant_uuid'] = tenant_uuid


def required_master_tenant():
    return auth_verifier.required_tenant(master_tenant_uuid)


def _get_master_tenant_uuid():
    if not app:
        raise Exception('Flask application not configured')

    tenant_uuid = app.config['auth']['master_tenant_uuid']
    if not tenant_uuid:
        raise _NotInitializedException()
    return tenant_uuid


def get_token_pbx_user_uuid_from_request(auth_client):
    token = request.headers.get('X-Auth-Token') or request.args.get('token')
    try:
        token_infos = auth_client.token.get(token)
    except HTTPError as e:
        logger.warning('HTTP error from wazo-auth while getting token: %s', e)
        raise TokenWithUserUUIDRequiredError()
    user_uuid = token_infos['metadata']['pbx_user_uuid']
    if not user_uuid:
        raise TokenWithUserUUIDRequiredError()
    return user_uuid


master_tenant_uuid = Proxy(_get_master_tenant_uuid)
