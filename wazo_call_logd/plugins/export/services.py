# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class ExportService:
    def __init__(self, dao):
        self._dao = dao

    def get(self, export_uuid, tenant_uuids):
        return self._dao.export.get(export_uuid, tenant_uuids)

    def create(self, *args, **kwargs):
        return self._dao.export.create(*args, **kwargs)

    def update(self, export):
        self._dao.export.update(export)


_service = None


def build_service(dao):
    global _service
    if _service is None:
        _service = ExportService(dao)
    return _service
