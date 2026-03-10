# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import Tenant, token

from wazo_call_logd.http import AuthResource

from .schemas import (
    TranscriptionListRequestSchema,
    TranscriptionListSchema,
    TranscriptionSchema,
)


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


class TranscriptionUserMeListResource(TranscriptionResource):
    @required_acl('call-logd.users.me.voicemails.transcriptions.read')
    def get(self):
        args = TranscriptionListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(recurse=True)
        user_uuid = token.user_uuid
        result = self.service.list_transcriptions(
            tenant_uuids=tenant_uuids, user_uuid=user_uuid, **args
        )
        return TranscriptionListSchema().dump(result)


class TranscriptionUserMeItemResource(TranscriptionResource):
    @required_acl(
        'call-logd.users.me.voicemails.transcriptions.{voicemail_message_id}.read'
    )
    def get(self, voicemail_message_id):
        tenant_uuids = self.visible_tenants(recurse=True)
        user_uuid = token.user_uuid
        transcription = self.service.get_transcription(
            voicemail_message_id,
            tenant_uuids=tenant_uuids,
            user_uuid=user_uuid,
        )
        return TranscriptionSchema().dump(transcription)


class TranscriptionUserListResource(TranscriptionResource):
    @required_acl('call-logd.users.{user_uuid}.voicemails.transcriptions.read')
    def get(self, user_uuid):
        args = TranscriptionListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(recurse=True)
        result = self.service.list_transcriptions(
            tenant_uuids=tenant_uuids, user_uuid=user_uuid, **args
        )
        return TranscriptionListSchema().dump(result)


class TranscriptionUserItemResource(TranscriptionResource):
    @required_acl(
        'call-logd.users.{user_uuid}.voicemails.transcriptions.{voicemail_message_id}.read'
    )
    def get(self, user_uuid, voicemail_message_id):
        tenant_uuids = self.visible_tenants(recurse=True)
        transcription = self.service.get_transcription(
            voicemail_message_id,
            tenant_uuids=tenant_uuids,
            user_uuid=user_uuid,
        )
        return TranscriptionSchema().dump(transcription)
