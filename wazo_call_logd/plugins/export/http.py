# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import g, send_file
from xivo import tenant_helpers

from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import auth_client, token, Tenant
from wazo_call_logd.auth import (
    extract_token_id_from_query_or_header,
)
from wazo_call_logd.http import AuthResource

from .exceptions import (
    ExportNotDoneYetException,
    ExportNotFoundException,
    ExportFSNotFoundException,
    ExportFSPermissionException,
)
from .schemas import (
    ExportSchema,
)

logger = logging.getLogger(__name__)


class ExportAuthResource(AuthResource):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def _set_up_token_helper_to_verify_tenant(self):
        token_uuid = extract_token_id_from_query_or_header()
        if not token_uuid:
            raise tenant_helpers.InvalidToken()
        g.token = tenant_helpers.Tokens(auth_client).get(token_uuid)
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


class ExportResource(ExportAuthResource):
    @required_acl('call-logd.exports.{export_uuid}.read')
    def get(self, export_uuid):
        tenant_uuids = self.visible_tenants(True)
        export = self.service.get(export_uuid, tenant_uuids)
        if not export:
            raise ExportNotFoundException(export_uuid)
        return ExportSchema().dump(export)


class ExportDownloadResource(ExportAuthResource):
    @required_acl(
        'call-logd.exports.{export_uuid}.download.read',
        extract_token_id=extract_token_id_from_query_or_header,
    )
    def get(self, export_uuid):
        tenant_uuids = self.query_or_header_visible_tenants(True)
        export = self.service.get(export_uuid, tenant_uuids)

        if not export:
            raise ExportNotFoundException(export_uuid)

        if not export.path:
            raise ExportNotFoundException(export_uuid)

        if not export.done:
            raise ExportNotDoneYetException(export_uuid)

        try:
            return send_file(
                export.path,
                mimetype='application/zip',
                as_attachment=True,
                attachment_filename=export.filename,
            )
        except PermissionError:
            logger.error('Permission denied: "%s"', export.path)
            raise ExportFSPermissionException(export_uuid, export.path)
        except FileNotFoundError:
            logger.error('Export file not found: "%s"', export.path)
            raise ExportFSNotFoundException(export_uuid, export.path)
