# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Range
from xivo.mallow_helpers import Schema


class RetentionSchema(Schema):
    tenant_uuid = fields.UUID(dump_only=True)
    cdr_days = fields.Integer(validate=Range(min=0), default=None, missing=None)
    recording_days = fields.Integer(validate=Range(min=0), default=None, missing=None)
