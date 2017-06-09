# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from flask import jsonify
from flask import make_response
from flask import request
from io import StringIO
from xivo.auth_verifier import required_acl
from xivo.unicode_csv import UnicodeDictWriter
from xivo_call_logs.core.auth import get_token_user_uuid_from_request
from xivo_call_logs.core.rest_api import AuthResource

from .schema import CDRSchemaList
from .schema import CDRListRequestSchema

logger = logging.getLogger(__name__)
CSV_HEADERS = ['id',
               'answered',
               'start',
               'answer',
               'end',
               'destination_extension',
               'destination_name',
               'duration',
               'call_direction',
               'source_extension',
               'source_name',
               'tags']


def _is_error(data):
    return 'error_id' in data


def _is_cdr_list(data):
    return 'items' in data


def _output_csv(data, code, http_headers=None):
    if _is_error(data):
        response = jsonify(data)
    elif _is_cdr_list(data):
        csv_text = StringIO()
        writer = UnicodeDictWriter(csv_text, CSV_HEADERS)

        writer.writeheader()
        for cdr in data['items']:
            if 'tags' in cdr:
                cdr['tags'] = '|'.join(cdr['tags'])
            writer.writerow(cdr)

        response = make_response(csv_text.getvalue())
    else:
        raise NotImplementedError('No known CSV representation')

    response.status_code = code
    response.headers.extend(http_headers or {})
    return response


class CDRResource(AuthResource):

    representations = {'text/csv; charset=utf-8': _output_csv}

    def __init__(self, cdr_service):
        self.cdr_service = cdr_service

    @required_acl('call-logd.cdr.read')
    def get(self):
        args = CDRListRequestSchema().load(request.args).data
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList().dump(cdrs).data


class CDRUserResource(AuthResource):

    representations = {'text/csv; charset=utf-8': _output_csv}

    def __init__(self, cdr_service):
        self.cdr_service = cdr_service

    @required_acl('call-logd.users.{user_uuid}.cdr.read')
    def get(self, user_uuid):
        args = CDRListRequestSchema(exclude=['user_uuid']).load(request.args).data
        args['user_uuids'] = [user_uuid]
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList().dump(cdrs).data


class CDRUserMeResource(AuthResource):

    representations = {'text/csv; charset=utf-8': _output_csv}

    def __init__(self, auth_client, cdr_service):
        self.auth_client = auth_client
        self.cdr_service = cdr_service

    @required_acl('call-logd.users.me.cdr.read')
    def get(self):
        args = CDRListRequestSchema(exclude=['user_uuid']).load(request.args).data
        user_uuid = get_token_user_uuid_from_request(self.auth_client)
        args['user_uuids'] = [user_uuid]
        cdrs = self.cdr_service.list(args)
        return CDRSchemaList(exclude=['items.tags']).dump(cdrs).data
