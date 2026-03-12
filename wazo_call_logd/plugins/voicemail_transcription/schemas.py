# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import pre_load
from xivo.mallow import fields
from xivo.mallow.validate import OneOf, Range
from xivo.mallow_helpers import Schema


class TranscriptionSchema(Schema):
    message_id = fields.String()
    tenant_uuid = fields.UUID()
    voicemail_id = fields.Integer()
    transcription_text = fields.String()
    provider_id = fields.String()
    language = fields.String()
    duration = fields.Float()
    created_at = fields.DateTime()


class TranscriptionListRequestSchema(Schema):
    limit = fields.Integer(validate=Range(min=0), load_default=1000)
    offset = fields.Integer(validate=Range(min=0), load_default=0)
    order = fields.String(
        validate=OneOf(['created_at', 'message_id']),
        load_default='created_at',
    )
    direction = fields.String(
        validate=OneOf(['asc', 'desc']),
        load_default='desc',
    )
    from_ = fields.DateTime(data_key='from', attribute='start', load_default=None)
    until = fields.DateTime(attribute='end', load_default=None)
    search_text = fields.String(load_default=None)
    voicemail_id = fields.List(fields.Integer(), load_default=None)

    @pre_load
    def convert_voicemail_id_to_list(self, data, **kwargs):
        result = data.to_dict()
        if data.get('voicemail_id'):
            result['voicemail_id'] = data['voicemail_id'].split(',')
        return result


class TranscriptionListSchema(Schema):
    items = fields.Nested(TranscriptionSchema, many=True)
    total = fields.Integer()
    filtered = fields.Integer()
