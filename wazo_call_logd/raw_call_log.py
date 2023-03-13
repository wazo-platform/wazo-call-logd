# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

import logging

from datetime import datetime
from wazo_call_logd.utils import defaultdict
from wazo_call_logd.database.models import CallLog, CallLogParticipant

from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd.extension_filter import (
    ExtensionFilter,
    DEFAULT_HIDDEN_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class RawCallLog:
    def __init__(self):
        self.date: datetime | None = None
        self.date_end: datetime | None = None
        self.source_name: str | None = None
        self.source_exten: str | None = None
        self.source_internal_exten: str | None = None
        self.source_internal_context: str | None = None
        self.source_internal_name: str | None = None
        self.source_user_uuid: str | None = None
        self.requested_name: str | None = None
        self.requested_exten: str | None = None
        self.requested_context: str | None = None
        self.requested_internal_exten: str | None = None
        self.requested_internal_context: str | None = None
        self.destination_name: str | None = None
        self.destination_exten: str | None = None
        self.destination_user_uuid: str | None = None
        self.destination_internal_exten: str | None = None
        self.destination_internal_context: str | None = None
        self.destination_line_identity: str | None = None
        self.user_field: str | None = None
        self.date_answer: datetime | None = None
        self.source_line_identity: str | None = None
        self.direction: Literal['source', 'destination', 'internal'] = 'internal'
        self.raw_participants: dict[str, dict] = defaultdict(default=dict)
        self.participants_info: list[dict] = []
        self.participants: list[CallLogParticipant] = []
        self.recordings: list = []
        self.cel_ids: list[int] = []
        self.interpret_callee_bridge_enter: bool = True
        self.interpret_caller_xivo_user_fwd: bool = True
        self._tenant_uuid: str = None  # type: ignore[assignment]
        self.pending_wait_for_mobile_peers: set[str] = set()
        self.caller_id_by_channels: dict[str, str] = {}
        self.extension_filter: ExtensionFilter = ExtensionFilter(
            DEFAULT_HIDDEN_EXTENSIONS
        )
        self.destination_details: list = []

    @property
    def tenant_uuid(self) -> str:
        return self._tenant_uuid

    def set_tenant_uuid(self, tenant_uuid):
        if self._tenant_uuid is None:
            self._tenant_uuid = str(tenant_uuid)
        elif self._tenant_uuid != tenant_uuid:
            logger.error(
                "We got a cel with an expected tenant_uuid: " "%s instead of %s",
                tenant_uuid,
                self._tenant_uuid,
            )

    def to_call_log(self) -> CallLog:
        if not self.date:
            raise InvalidCallLogException('date not found')
        if not (self.source_name or self.source_exten):
            raise InvalidCallLogException('source name and exten not found')

        result = CallLog(
            tenant_uuid=self._tenant_uuid,
            date=self.date,
            date_answer=self.date_answer,
            date_end=self.date_end,
            source_name=self.source_name,
            source_exten=self.source_exten,
            source_internal_exten=self.source_internal_exten,
            source_internal_context=self.source_internal_context,
            source_internal_name=self.source_internal_name,
            requested_exten=self.requested_exten,
            requested_context=self.requested_context,
            requested_internal_exten=self.requested_internal_exten,
            requested_internal_context=self.requested_internal_context,
            requested_name=self.requested_name,
            destination_name=self.destination_name,
            destination_exten=self.destination_exten,
            destination_internal_exten=self.destination_internal_exten,
            destination_internal_context=self.destination_internal_context,
            destination_line_identity=self.destination_line_identity,
            user_field=self.user_field,
            source_line_identity=self.source_line_identity,
            direction=self.direction,
            destination_details=self.destination_details,
        )
        result.participants = self.participants
        result.cel_ids = self.cel_ids
        result.recordings = self.recordings

        return result
