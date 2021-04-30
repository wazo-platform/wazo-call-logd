# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import token, Tenant
from wazo_call_logd.http import AuthResource

from .exceptions import ExportNotFoundException
from .schemas import (
    ExportSchema,
)


class ExportAuthResource(AuthResource):
    def __init__(self, service, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service

    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]


class ExportResource(ExportAuthResource):
    @required_acl('call-logd.exports.{export_uuid}.read')
    def get(self, export_uuid):
        tenant_uuids = self.visible_tenants(True)
        export = self.service.get(export_uuid, tenant_uuids)
        if not export:
            raise ExportNotFoundException(export_uuid)
        return ExportSchema().dump(export)
