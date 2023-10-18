# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from dataclasses import dataclass

from wazo_call_logd.database.queries.tenant import TenantDAO

from ...sync_db import remove_tenant

logger = logging.getLogger(__name__)


@dataclass
class TenantEventHandler:
    tenant_dao: TenantDAO

    def subscribe(self, bus_consumer):
        bus_consumer.subscribe('auth_tenant_deleted', self._auth_tenant_deleted)

    def _auth_tenant_deleted(self, event):
        with self.tenant_dao.new_session() as session:
            remove_tenant(event['uuid'], session)
