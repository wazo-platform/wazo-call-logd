# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import BaseDAO
from ..models import Config, Retention, Tenant


class RetentionDAO(BaseDAO):
    def find(self, tenant_uuid):
        with self.new_session() as session:
            query = session.query(Retention)
            query = query.filter(Retention.tenant_uuid == tenant_uuid)
            retention = query.first()
            if not retention:
                retention = Retention(tenant_uuid=tenant_uuid)
            else:
                session.flush()
                session.expunge(retention)
            config = session.query(Config).first()
            retention.default_cdr_days = config.retention_cdr_days
            retention.default_recording_days = config.retention_recording_days
        return retention

    def find_or_create(self, tenant_uuid):
        with self.new_session() as session:
            query = session.query(Retention)
            query = query.filter(Retention.tenant_uuid == tenant_uuid)
            retention = query.first()
            if not retention:
                tenant = self._find_or_create_tenant(session, tenant_uuid)
                retention = Retention(tenant_uuid=tenant.uuid)
                session.add(retention)
            config = session.query(Config).first()
            retention.default_cdr_days = config.retention_cdr_days
            retention.default_recording_days = config.retention_recording_days
            session.flush()
            session.expunge(retention)
        return retention

    def _find_or_create_tenant(self, session, tenant_uuid):
        tenant = session.query(Tenant).get(tenant_uuid)
        if not tenant:
            tenant = Tenant(uuid=tenant_uuid)
            session.add(tenant)
            session.flush()
        return tenant

    def update(self, retention):
        with self.new_session() as session:
            session.add(retention)
            session.flush()
            session.expunge(retention)
