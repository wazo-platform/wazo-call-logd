# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wazo_call_logd.database.models import Export
    from wazo_call_logd.database.queries import DAO


class ExportService:
    def __init__(self, dao: DAO) -> None:
        self._dao = dao

    def get(self, export_uuid: str, tenant_uuids: list[str]) -> Export:
        return self._dao.export.get(export_uuid, tenant_uuids)

    def create(self, *args: Any, **kwargs: Any) -> Export:
        return self._dao.export.create(*args, **kwargs)

    def update(self, export: Export) -> None:
        self._dao.export.update(export)
