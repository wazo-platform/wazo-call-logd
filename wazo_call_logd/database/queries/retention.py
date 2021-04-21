# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import BaseDAO
from ..models import Retention


class RetentionDAO(BaseDAO):
    def find(self, tenant_uuid):
        with self.new_session() as session:
            query = session.query(Retention)
            query = query.filter(Retention.tenant_uuid == tenant_uuid)
            retention = query.first()
            if not retention:
                return
            session.flush()
            session.expunge(retention)
        return retention

    def find_or_create(self, tenant_uuid):
        with self.new_session() as session:
            query = session.query(Retention)
            query = query.filter(Retention.tenant_uuid == tenant_uuid)
            retention = query.first()
            if not retention:
                retention = Retention(tenant_uuid=tenant_uuid)
                session.add(retention)
            session.flush()
            session.expunge(retention)
        return retention

    def update(self, retention):
        with self.new_session() as session:
            session.add(retention)
            session.flush()
            session.expunge(retention)
