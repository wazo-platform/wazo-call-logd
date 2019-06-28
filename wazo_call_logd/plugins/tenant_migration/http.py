# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request

from xivo.auth_verifier import required_acl
from wazo_call_logd.rest_api import AuthResource


class CallLogdTenantUpgradeResource(AuthResource):

    def __init__(self, service):
        self._service = service

    @required_acl('webhookd.tenant-upgrade')
    def post(self):
        for item in request.json:
            self._service.update_tenant_uuid(**item)
