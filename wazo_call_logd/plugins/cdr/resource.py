# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import csv

from io import StringIO

from flask import jsonify, make_response, request
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import token, Tenant
from wazo_call_logd.auth import get_token_user_uuid_from_request
from wazo_call_logd.http import AuthResource

from .exceptions import CDRNotFoundException
from .schema import CDRSchema, CDRSchemaList, CDRListRequestSchema

logger = logging.getLogger(__name__)
CSV_HEADERS = [
    'id',
    'tenant_uuid',
    'answered',
    'start',
    'answer',
    'end',
    'destination_extension',
    'destination_name',
    'destination_internal_extension',
    'destination_internal_context',
    'destination_user_uuid',
    'destination_line_id',
    'duration',
    'call_direction',
    'requested_name',
    'requested_extension',
    'requested_context',
    'requested_internal_extension',
    'requested_internal_context',
    'source_extension',
    'source_name',
    'source_internal_extension',
    'source_internal_context',
    'source_user_uuid',
    'source_line_id',
    'tags',
]


def _is_error(data):
    return 'error_id' in data


def _is_cdr_list(data):
    return 'items' in data


def _is_single_cdr(data):
    return 'id' in data and 'tags' in data


def _output_csv(data, code, http_headers=None):
    if _is_error(data):
        response = jsonify(data)
    elif _is_cdr_list(data) or _is_single_cdr(data):
        csv_text = StringIO()
        writer = csv.DictWriter(csv_text, CSV_HEADERS)

        writer.writeheader()
        items = data['items'] if _is_cdr_list(data) else [data]
        for cdr in items:
            if 'tags' in cdr:
                cdr['tags'] = ';'.join(cdr['tags'])
            writer.writerow(cdr)

        response = make_response(csv_text.getvalue())
    else:
        raise NotImplementedError('No known CSV representation')

    response.status_code = code
    response.headers.extend(http_headers or {})
    return response


class CDRAuthResource(AuthResource):
    representations = {'text/csv; charset=utf-8': _output_csv}

    def __init__(self, cdr_service):
        super().__init__()
        self.cdr_service = cdr_service

    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]


class CDRResource(CDRAuthResource):
    @required_acl('call-logd.cdr.read')
    def get(self):
        args = CDRListRequestSchema().load(request.args)
        args["tenant_uuids"] = self.visible_tenants(args["recurse"])
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList().dump(cdrs)


class CDRIdResource(CDRAuthResource):
    @required_acl('call-logd.cdr.{cdr_id}.read')
    def get(self, cdr_id):
        tenant_uuids = self.visible_tenants(True)
        cdr = self.cdr_service.get(cdr_id, tenant_uuids)
        if not cdr:
            raise CDRNotFoundException(details={'cdr_id': cdr_id})
        return CDRSchema().dump(cdr)


class CDRUserResource(CDRAuthResource):
    @required_acl('call-logd.users.{user_uuid}.cdr.read')
    def get(self, user_uuid):
        args = CDRListRequestSchema(exclude=['user_uuid']).load(request.args)
        args['user_uuids'] = [user_uuid]
        args['tenant_uuids'] = [Tenant.autodetect().uuid]
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList().dump(cdrs)


class CDRUserMeResource(CDRAuthResource):
    def __init__(self, auth_client, cdr_service):
        super().__init__(cdr_service)
        self.auth_client = auth_client

    @required_acl('call-logd.users.me.cdr.read')
    def get(self):
        args = CDRListRequestSchema().load(request.args)
        user_uuid = get_token_user_uuid_from_request(self.auth_client)
        args['me_user_uuid'] = user_uuid
        args['tenant_uuids'] = [token.tenant_uuid]
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList(exclude=['items.tags']).dump(cdrs)
