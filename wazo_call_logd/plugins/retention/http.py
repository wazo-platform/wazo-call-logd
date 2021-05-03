# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request

from wazo_call_logd.http import AuthResource
from xivo.auth_verifier import required_acl
from xivo.tenant_flask_helpers import Tenant

from .schemas import RetentionSchema


def update_model_instance(model_instance, model_instance_data):
    for attribute_name, attribute_value in model_instance_data.items():
        if not hasattr(model_instance, attribute_name):
            model_name = model_instance.__class__.__name__
            raise TypeError(f'{model_name} has no attribute {attribute_name}')
        setattr(model_instance, attribute_name, attribute_value)


class RetentionResource(AuthResource):
    def __init__(self, service):
        super().__init__()
        self.service = service

    @required_acl('call-logd.retention.read')
    def get(self):
        tenant_uuid = Tenant.autodetect().uuid
        retention = self.service.find(tenant_uuid)
        result = RetentionSchema().dump(retention)
        if not retention:
            result['tenant_uuid'] = tenant_uuid
        return result

    @required_acl('call-logd.retention.read')
    def put(self):
        tenant_uuid = Tenant.autodetect().uuid
        retention = self.service.find_or_create(tenant_uuid)
        retention_args = RetentionSchema().load(request.get_json())
        update_model_instance(retention, retention_args)
        self.service.update(retention)
        return '', 204
