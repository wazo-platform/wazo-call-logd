# Copyright 2017-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import logging
from io import StringIO

from flask import g, jsonify, make_response, request, send_file, url_for
from xivo import tenant_helpers
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import Tenant, auth_client, token

from wazo_call_logd.auth import (
    extract_token_id_from_query_or_header,
    get_token_pbx_user_uuid_from_request,
)
from wazo_call_logd.http import AuthResource
from wazo_call_logd.plugin_helpers.flask import extract_connection_params

from .exceptions import (
    CDRNotFoundException,
    CDRRecordingMediaFSPermissionException,
    NoRecordingToExportException,
    RecordingMediaFSNotFoundException,
    RecordingMediaFSPermissionException,
    RecordingMediaNotFoundException,
    RecordingNotFoundException,
)
from .schemas import (
    CDRListRequestSchema,
    CDRSchema,
    CDRSchemaList,
    RecordingMediaDeleteRequestSchema,
    RecordingMediaExportBodySchema,
    RecordingMediaExportRequestSchema,
    RecordingMediaExportSchema,
)

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
    'requested_user_uuid',
    'source_extension',
    'source_name',
    'source_internal_name',
    'source_internal_extension',
    'source_internal_context',
    'source_user_uuid',
    'source_line_id',
    'tags',
    # recording_{x}_{key},  # Added dynamically
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
        csv_headers = CSV_HEADERS.copy()
        csv_body = []
        items = data['items'] if _is_cdr_list(data) else [data]
        for cdr in items:
            if 'tags' in cdr:
                cdr['tags'] = ';'.join(cdr['tags'])

            for x, recording in enumerate(cdr.pop('recordings'), start=1):
                for key in recording.keys():
                    csv_key = f'recording_{x}_{key}'
                    if csv_key not in csv_headers:
                        csv_headers.append(csv_key)
                    cdr[csv_key] = recording[key]

            csv_body.append(cdr)

        csv_text = StringIO()
        writer = csv.DictWriter(csv_text, csv_headers, extrasaction='ignore')
        writer.writeheader()
        for csv_line in csv_body:
            writer.writerow(csv_line)

        response = make_response(
            csv_text.getvalue(),
            {'Content-Disposition': 'attachment; filename=cdr.csv'},
        )
    else:
        raise NotImplementedError('No known CSV representation')

    response.status_code = code
    response.headers.extend(http_headers or {})
    return response


def request_wants_csv():
    best = request.accept_mimetypes.best_match(
        ['text/csv; charset=utf-8', 'application/json']
    )
    csv_header = (
        best == 'text/csv; charset=utf-8'
        and request.accept_mimetypes[best]
        > request.accept_mimetypes['application/json']
    )
    return request.args.get('format') == 'csv' or csv_header


def format_cdr_result(result):
    if request_wants_csv():
        return _output_csv(result, 200)
    else:
        return result


class CDRAuthResource(AuthResource):
    def __init__(self, service):
        super().__init__()
        self.cdr_service = service

    def _set_up_token_helper_to_verify_tenant(self):
        token_uuid = extract_token_id_from_query_or_header()
        if not token_uuid:
            raise tenant_helpers.InvalidTokenAPIException()
        g.token = tenant_helpers.Token(token_uuid, auth_client)
        auth_client.set_token(g.token.uuid)

    def query_or_header_visible_tenants(self, recurse=True):
        self._set_up_token_helper_to_verify_tenant()
        tenant_uuid = Tenant.autodetect(include_query=True).uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]

    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]


class CDRResource(CDRAuthResource):
    @required_acl(
        'call-logd.cdr.read', extract_token_id=extract_token_id_from_query_or_header
    )
    def get(self):
        args = CDRListRequestSchema().load(request.args)
        args['tenant_uuids'] = self.query_or_header_visible_tenants(args['recurse'])
        cdrs = self.cdr_service.list(args)
        return format_cdr_result(CDRSchemaList().dump(cdrs))


class CDRIdResource(CDRAuthResource):
    @required_acl('call-logd.cdr.{cdr_id}.read')
    def get(self, cdr_id):
        tenant_uuids = self.visible_tenants(recurse=True)
        cdr = self.cdr_service.get(cdr_id, tenant_uuids)
        if not cdr:
            raise CDRNotFoundException(details={'cdr_id': cdr_id})
        return format_cdr_result(CDRSchema().dump(cdr))


class CDRUserResource(CDRAuthResource):
    @required_acl(
        'call-logd.users.{user_uuid}.cdr.read',
        extract_token_id=extract_token_id_from_query_or_header,
    )
    def get(self, user_uuid):
        args = CDRListRequestSchema(exclude=['user_uuid']).load(request.args)
        args['user_uuids'] = [user_uuid]
        args['tenant_uuids'] = self.query_or_header_visible_tenants(args['recurse'])
        cdrs = self.cdr_service.list(args)
        return format_cdr_result(CDRSchemaList().dump(cdrs))


class CDRUserMeResource(CDRAuthResource):
    def __init__(self, auth_client, cdr_service):
        super().__init__(cdr_service)
        self.auth_client = auth_client

    @required_acl(
        'call-logd.users.me.cdr.read',
        extract_token_id=extract_token_id_from_query_or_header,
    )
    def get(self):
        args = CDRListRequestSchema().load(request.args)
        user_uuid = get_token_pbx_user_uuid_from_request(self.auth_client)
        args['me_user_uuid'] = user_uuid
        args['tenant_uuids'] = self.query_or_header_visible_tenants(recurse=False)
        cdrs = self.cdr_service.list(args)
        return format_cdr_result(CDRSchemaList(exclude=['items.tags']).dump(cdrs))


class RecordingsMediaExportResource(CDRAuthResource):
    def __init__(self, recording_service, cdr_service, api):
        super().__init__(cdr_service)
        self.recording_service = recording_service
        self.api = api

    @required_acl('call-logd.cdr.recordings.media.export.create')
    def post(self):
        args = RecordingMediaExportRequestSchema().load(request.args)
        body_args = RecordingMediaExportBodySchema().load(request.get_json(force=True))
        args['tenant_uuids'] = self.visible_tenants(args['recurse'])
        args['cdr_ids'] = body_args['cdr_ids']

        recordings_to_download = []
        call_logs = self.cdr_service.list(args)['items']
        for cdr in call_logs:
            for recording in cdr.recordings:
                if recording.path:
                    recordings_to_download.append(recording)

        if not recordings_to_download:
            raise NoRecordingToExportException()

        destination_email = args['email']
        connection_info = extract_connection_params(request.headers)
        export = self.recording_service.start_recording_export(
            recordings_to_download,
            token.user_uuid,
            token.tenant_uuid,
            destination_email,
            connection_info,
        )
        export_body = RecordingMediaExportSchema().dump(export)
        location = url_for('export_resource', export_uuid=export['uuid'])
        headers = {'Location': location}

        return export_body, 202, headers


class RecordingsMediaResource(CDRAuthResource):
    def __init__(self, recording_service, cdr_service):
        super().__init__(cdr_service)
        self.recording_service = recording_service

    @required_acl('call-logd.cdr.recordings.media.delete')
    def delete(self):
        args = RecordingMediaDeleteRequestSchema().load(request.get_json(force=True))
        tenant_uuids = self.visible_tenants(recurse=True)
        call_log_ids = args['cdr_ids']
        recordings_to_delete = []
        # We do not want to delete any recording if one of the CDR has not been found
        for cdr_id in call_log_ids:
            cdr = self.cdr_service.get(cdr_id, tenant_uuids)
            if not cdr:
                raise CDRNotFoundException(details={'cdr_id': cdr_id})
            recordings_to_delete.extend(cdr.recordings)

        for recording in recordings_to_delete:
            try:
                self.recording_service.delete_media(
                    recording.call_log_id, recording.uuid, recording.path
                )
            except PermissionError:
                logger.error('Permission denied: "%s"', recording.path)
                raise CDRRecordingMediaFSPermissionException(
                    recording.call_log_id, recording.uuid, recording.path
                )
            except FileNotFoundError:
                logger.info(
                    'Recording file already deleted: "%s". Marking as such.',
                    recording.path,
                )
        return '', 204


class RecordingMediaItemResource(CDRAuthResource):
    def __init__(self, recording_service, cdr_service):
        super().__init__(cdr_service)
        self.recording_service = recording_service

    @required_acl(
        'call-logd.cdr.{cdr_id}.recordings.{recording_uuid}.media.read',
        extract_token_id=extract_token_id_from_query_or_header,
    )
    def get(self, cdr_id, recording_uuid):
        tenant_uuids = self.query_or_header_visible_tenants(recurse=True)
        cdr = self.cdr_service.get(cdr_id, tenant_uuids)
        if not cdr:
            raise CDRNotFoundException(details={'cdr_id': cdr_id})

        recording = self.recording_service.find_by(
            uuid=recording_uuid, call_log_id=cdr_id
        )
        if not recording:
            raise RecordingNotFoundException(recording_uuid)

        if not recording.path:
            raise RecordingMediaNotFoundException(recording_uuid)

        try:
            return send_file(
                recording.path,
                mimetype='audio/wav',
                as_attachment=True,
                attachment_filename=recording.filename,
            )
        except PermissionError:
            logger.error('Permission denied: "%s"', recording.path)
            raise RecordingMediaFSPermissionException(recording_uuid, recording.path)
        except FileNotFoundError:
            logger.error('Recording file not found: "%s"', recording.path)
            raise RecordingMediaFSNotFoundException(recording_uuid, recording.path)

    @required_acl('call-logd.cdr.{cdr_id}.recordings.{recording_uuid}.media.delete')
    def delete(self, cdr_id, recording_uuid):
        tenant_uuids = self.visible_tenants(recurse=True)
        cdr = self.cdr_service.get(cdr_id, tenant_uuids)
        if not cdr:
            raise CDRNotFoundException(details={'cdr_id': cdr_id})

        recording = self.recording_service.find_by(
            uuid=recording_uuid, call_log_id=cdr_id
        )
        if not recording:
            raise RecordingNotFoundException(recording_uuid)

        try:
            self.recording_service.delete_media(cdr_id, recording_uuid, recording.path)
        except PermissionError:
            logger.error('Permission denied: "%s"', recording.path)
            raise RecordingMediaFSPermissionException(recording_uuid, recording.path)
        except FileNotFoundError:
            logger.info(
                'Recording file already deleted: "%s". Marking as such.', recording.path
            )
        return '', 204


class RecordingMediaItemUserMeResource(CDRAuthResource):
    def __init__(self, recording_service, cdr_service, auth_client):
        super().__init__(cdr_service)
        self.auth_client = auth_client
        self.recording_service = recording_service

    @required_acl(
        'call-logd.users.me.cdr.{cdr_id}.recordings.{recording_uuid}.media.read',
    )
    def get(self, cdr_id, recording_uuid):
        user_uuid = get_token_pbx_user_uuid_from_request(self.auth_client)
        tenant_uuids = self.query_or_header_visible_tenants(recurse=False)
        cdr = self.cdr_service.get(cdr_id, tenant_uuids, user_uuids=[user_uuid])
        if not cdr:
            raise CDRNotFoundException(details={'cdr_id': cdr_id})

        recording = self.recording_service.find_by(
            uuid=recording_uuid, call_log_id=cdr_id
        )
        if not recording:
            raise RecordingNotFoundException(recording_uuid)

        if not recording.path:
            raise RecordingMediaNotFoundException(recording_uuid)

        try:
            return send_file(
                recording.path,
                mimetype='audio/wav',
                as_attachment=True,
                attachment_filename=recording.filename,
            )
        except PermissionError:
            logger.error('Permission denied: "%s"', recording.path)
            raise RecordingMediaFSPermissionException(recording_uuid, recording.path)
        except FileNotFoundError:
            logger.error('Recording file not found: "%s"', recording.path)
            raise RecordingMediaFSNotFoundException(recording_uuid, recording.path)
