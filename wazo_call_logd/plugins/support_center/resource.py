# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging


from flask import request
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import token, Tenant
from wazo_call_logd.rest_api import AuthResource

from .exceptions import QueueNotFoundException
from .schema import QueueStatisticsListRequestSchema, QueueStatisticsSchemaList

logger = logging.getLogger(__name__)


class QueuesStatisticsAuthResource(AuthResource):

    def __init__(self, queue_statistics_service):
        super().__init__()
        self.queue_statistics_service = queue_statistics_service

    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]

class QueuesStatisticsResource(QueuesStatisticsAuthResource):
    @required_acl('call-logd.queues.statistics.read')
    def get(self):
        args = QueueStatisticsListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        cdrs = self.queue_statistics_service.list(tenant_uuids, **args)
        return QueueStatisticsSchemaList().dump(cdrs)


class QueueStatisticsResource(QueuesStatisticsAuthResource):
    @required_acl('call-logd.queues.{queue_id}.statistics.read')
    def get(self, queue_id):
        tenant_uuids = self.visible_tenants(True)
        queue_stats = self.queue_statistics_service.get(tenant_uuids, queue_id, **kwargs)
        if not queue_stats:
            raise QueueNotFoundException(details={'queue_id': queue_id})
        return QueueStatisticsSchemaList().dump(queue_stats)
