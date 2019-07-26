# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_call_logd.rest_api import api

from . import http, service


# This plugin is used for the tenant uuid migration between wazo-auth and webhookd
class Plugin(object):
    def load(self, dependencies):
        config = dependencies['config']
        token_renewer = dependencies['token_renewer']

        tenant_upgrade_service = service.CallLogdTenantUpgradeService(config)
        token_renewer.subscribe_to_next_token_details_change(
            tenant_upgrade_service.set_default_tenant_uuid
        )
        api.add_resource(
            http.CallLogdTenantUpgradeResource,
            '/tenant-migration',
            resource_class_args=[tenant_upgrade_service],
        )
