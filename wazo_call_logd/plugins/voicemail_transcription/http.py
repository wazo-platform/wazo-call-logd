# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import Tenant, token

from wazo_call_logd.http import AuthResource

from .schemas import TranscriptionListRequestSchema, TranscriptionListSchema


class TranscriptionResource(AuthResource):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]


class TranscriptionListResource(TranscriptionResource):
    @required_acl('call-logd.voicemails.transcriptions.read')
    def get(self):
        args = TranscriptionListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(recurse=True)
        result = self.service.list_transcriptions(tenant_uuids=tenant_uuids, **args)
        return TranscriptionListSchema().dump(result)
