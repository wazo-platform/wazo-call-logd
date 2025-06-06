# Copyright 2021-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import validates_schema
from marshmallow.exceptions import ValidationError
from xivo.mallow import fields
from xivo.mallow.validate import Range
from xivo.mallow_helpers import Schema


class RetentionSchema(Schema):
    tenant_uuid = fields.UUID(dump_only=True)
    cdr_days = fields.Integer(validate=Range(min=0), load_default=None)
    export_days = fields.Integer(validate=Range(min=0), load_default=None)
    recording_days = fields.Integer(validate=Range(min=0), load_default=None)
    default_cdr_days = fields.Integer(dump_only=True)
    default_export_days = fields.Integer(dump_only=True)
    default_recording_days = fields.Integer(dump_only=True)

    @validates_schema
    def validate_days(self, data, **kwargs):
        cdr_days = data.get('cdr_days')
        recording_days = data.get('recording_days')
        if cdr_days is None or recording_days is None:
            return

        if recording_days > cdr_days:
            raise ValidationError(
                '"recording_days" must be higher or equal than "cdr_days"',
                field_name='recording_days',
            )
