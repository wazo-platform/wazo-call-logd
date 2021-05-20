# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import text

from .base import BaseDAO
from ..models import Export
from ...exceptions import ExportNotFoundException


class ExportDAO(BaseDAO):
    def get_by_uuid(self, export_uuid, tenant_uuids=None):
        with self.new_session() as session:
            query = session.query(Export)
            query = self._apply_filters(query, {'tenant_uuids': tenant_uuids})
            query = query.filter(Export.uuid == export_uuid)
            export = query.one_or_none()
            if not export:
                raise ExportNotFoundException(export_uuid)
            session.expunge_all()
            return export

    def _add_tenant_filter(self, query, tenant_uuids):
        if tenant_uuids:
            query = query.filter(Export.tenant_uuid.in_(tenant_uuids))
        elif not tenant_uuids and tenant_uuids is not None:
            query = query.filter(text('false'))
        return query

    def _apply_filters(self, query, params):
        query = self._add_tenant_filter(query, params.get('tenant_uuids'))
        return query

    def create(self, export_uuid, user_uuid, tenant_uuid, date):
        with self.new_session() as session:
            export = Export(
                uuid=export_uuid,
                user_uuid=user_uuid,
                tenant_uuid=tenant_uuid,
                date=date,
            )
            session.add(export)
            session.flush()
            session.expunge(export)
        return export

    def update(self, export):
        with self.new_session() as session:
            session.add(export)
            session.flush()
            session.expunge(export)
