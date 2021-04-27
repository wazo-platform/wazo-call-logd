# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.auth import required_master_tenant
from wazo_call_logd.http import AuthResource
from xivo.auth_verifier import required_acl


class ConfigResource(AuthResource):
    def __init__(self, config_service):
        self._config_service = config_service

    @required_master_tenant()
    @required_acl('call_logd.config.read')
    def get(self):
        return self._config_service.get(), 200
