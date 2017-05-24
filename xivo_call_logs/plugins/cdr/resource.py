# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from flask import request
from xivo.auth_verifier import required_acl
from xivo_call_logs.core.auth import get_token_user_uuid_from_request
from xivo_call_logs.core.rest_api import AuthResource

from .schema import CDRSchemaList
from .schema import list_schema


class CDRResource(AuthResource):

    def __init__(self, cdr_service):
        self.cdr_service = cdr_service

    @required_acl('call-logd.cdr.read')
    def get(self):
        args = list_schema.load(request.args).data
        cdrs = self.cdr_service.list(**args)
        return CDRSchemaList().dump(cdrs).data


class CDRUserResource(AuthResource):

    def __init__(self, cdr_service):
        self.cdr_service = cdr_service

    @required_acl('call-logd.users.{user_uuid}.cdr.read')
    def get(self, user_uuid):
        args = list_schema.load(request.args).data
        cdrs = self.cdr_service.list(user_uuids=[user_uuid], **args)
        return CDRSchemaList().dump(cdrs).data


class CDRUserMeResource(AuthResource):

    def __init__(self, auth_client, cdr_service):
        self.auth_client = auth_client
        self.cdr_service = cdr_service

    @required_acl('call-logd.users.me.cdr.read')
    def get(self):
        args = list_schema.load(request.args).data
        user_uuid = get_token_user_uuid_from_request(self.auth_client)
        cdrs = self.cdr_service.list(user_uuids=[user_uuid], **args)
        return CDRSchemaList(exclude=['items.tags']).dump(cdrs).data
