# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import token, Tenant
from wazo_call_logd.http import AuthResource

from .schemas import (
    AgentStatisticsListRequestSchema,
    AgentStatisticsRequestSchema,
    AgentStatisticsSchemaList,
    QueueStatisticsListRequestSchema,
    QueueStatisticsRequestSchema,
    QueueStatisticsQoSRequestSchema,
    QueueStatisticsSchemaList,
    QueueStatisticsQoSSchemaList,
)


class _MultiTenantAuthResource(AuthResource):
    def visible_tenants(self, recurse=True):
        tenant_uuid = Tenant.autodetect().uuid
        if recurse:
            return [tenant.uuid for tenant in token.visible_tenants(tenant_uuid)]
        else:
            return [tenant_uuid]


class AgentsStatisticsAuthResource(_MultiTenantAuthResource):
    def __init__(self, agent_statistics_service):
        super().__init__()
        self.agent_statistics_service = agent_statistics_service


class AgentsStatisticsResource(AgentsStatisticsAuthResource):
    @required_acl('call-logd.agents.statistics.read')
    def get(self):
        args = AgentStatisticsListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        queue_stats = self.agent_statistics_service.list(tenant_uuids, **args)
        return AgentStatisticsSchemaList().dump(queue_stats)


class AgentStatisticsResource(AgentsStatisticsAuthResource):
    @required_acl('call-logd.agents.{agent_id}.statistics.read')
    def get(self, agent_id):
        args = AgentStatisticsRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        agent_stats = self.agent_statistics_service.get(tenant_uuids, agent_id, **args)
        return AgentStatisticsSchemaList().dump(agent_stats)


class QueuesStatisticsAuthResource(_MultiTenantAuthResource):
    def __init__(self, queue_statistics_service):
        super().__init__()
        self.queue_statistics_service = queue_statistics_service


class QueuesStatisticsResource(QueuesStatisticsAuthResource):
    @required_acl('call-logd.queues.statistics.read')
    def get(self):
        args = QueueStatisticsListRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        queue_stats = self.queue_statistics_service.list(tenant_uuids, **args)
        return QueueStatisticsSchemaList().dump(queue_stats)


class QueueStatisticsResource(QueuesStatisticsAuthResource):
    @required_acl('call-logd.queues.{queue_id}.statistics.read')
    def get(self, queue_id):
        args = QueueStatisticsRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        queue_stats = self.queue_statistics_service.get(tenant_uuids, queue_id, **args)
        return QueueStatisticsSchemaList().dump(queue_stats)


class QueueStatisticsQoSResource(QueuesStatisticsAuthResource):
    @required_acl('call-logd.queues.{queue_id}.statistics.qos.read')
    def get(self, queue_id):
        args = QueueStatisticsQoSRequestSchema().load(request.args)
        tenant_uuids = self.visible_tenants(True)
        queue_stats = self.queue_statistics_service.get_qos(
            tenant_uuids, queue_id, **args
        )
        return QueueStatisticsQoSSchemaList().dump(queue_stats)
