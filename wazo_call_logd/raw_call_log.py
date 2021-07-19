# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import defaultdict
from wazo_call_logd.database.models import CallLog

from wazo_call_logd.exceptions import InvalidCallLogException

logger = logging.getLogger(__name__)


class RawCallLog:
    def __init__(self):
        self.date = None
        self.date_end = None
        self.source_name = None
        self.source_exten = None
        self.source_internal_exten = None
        self.source_internal_context = None
        self.source_internal_name = None
        self.requested_name = None
        self.requested_exten = None
        self.requested_context = None
        self.requested_internal_exten = None
        self.requested_internal_context = None
        self.destination_name = None
        self.destination_exten = None
        self.destination_internal_exten = None
        self.destination_internal_context = None
        self.destination_line_identity = None
        self.user_field = None
        self.date_answer = None
        self.source_line_identity = None
        self.direction = 'internal'
        self.raw_participants = defaultdict(dict)
        self.participants = []
        self.participants_by_channame = {}
        self.recordings = []
        self.cel_ids = []
        self.interpret_callee_bridge_enter = True
        self.interpret_caller_xivo_user_fwd = True
        self._tenant_uuid = None

    @property
    def tenant_uuid(self):
        return self._tenant_uuid

    def set_tenant_uuid(self, tenant_uuid):
        if self._tenant_uuid is None:
            self._tenant_uuid = tenant_uuid
        elif self._tenant_uuid != tenant_uuid:
            logger.error(
                "We got a cel with an expected tenant_uuid: " "%s instead of %s",
                tenant_uuid,
                self._tenant_uuid,
            )

    def to_call_log(self):
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
        )
        result.participants = self.participants
        result.cel_ids = self.cel_ids
        result.recordings = self.recordings

        return result
