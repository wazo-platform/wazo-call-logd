# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import (
    EXCLUDE,
    fields,
    post_load,
    Schema,
    pre_dump,
    pre_load,
    post_dump,
)
from marshmallow.validate import OneOf, Range, Regexp

NUMBER_REGEX = r'^_?[0-9]+_?$'


class CDRSchema(Schema):
    class Meta(object):
        ordered = True
        unknown = EXCLUDE

    id = fields.Integer()
    tenant_uuid = fields.UUID()
    start = fields.DateTime(attribute='date')
    end = fields.DateTime(attribute='date_end')
    answered = fields.Boolean(attribute='marshmallow_answered')
    answer = fields.DateTime(attribute='date_answer')
    duration = fields.TimeDelta(default=None, attribute='marshmallow_duration')
    call_direction = fields.String(attribute='direction')
    destination_extension = fields.String(attribute='destination_exten')
    destination_internal_context = fields.String()
    destination_internal_extension = fields.String(
        attribute='destination_internal_exten'
    )
    destination_line_id = fields.Integer()
    destination_name = fields.String()
    destination_user_uuid = fields.UUID()
    requested_context = fields.String()
    requested_extension = fields.String(attribute='requested_exten')
    requested_internal_context = fields.String()
    requested_internal_extension = fields.String(attribute='requested_internal_exten')
    source_extension = fields.String(attribute='source_exten')
    source_internal_context = fields.String()
    source_internal_extension = fields.String(attribute='source_internal_exten')
    source_line_id = fields.Integer()
    source_name = fields.String()
    source_user_uuid = fields.UUID()
    tags = fields.List(fields.String(), attribute='marshmallow_tags')

    @pre_dump
    def _compute_fields(self, data):
        data.marshmallow_answered = True if data.date_answer else False
        if data.date_answer and data.date_end:
            data.marshmallow_duration = data.date_end - data.date_answer
        return data

    @post_dump
    def fix_negative_duration(self, data):
        if data['duration'] is not None:
            data['duration'] = max(data['duration'], 0)
        return data

    @pre_dump
    def _populate_tags_field(self, data):
        data.marshmallow_tags = set()
        for participant in data.participants:
            data.marshmallow_tags.update(participant.tags)
        return data


class CDRListRequestSchema(Schema):
    from_ = fields.DateTime(data_key='from', attribute='start', missing=None)
    until = fields.DateTime(attribute='end', missing=None)
    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='desc')
    order = fields.String(
        validate=OneOf(set(CDRSchema().fields) - {'end', 'tags'}), missing='start'
    )
    limit = fields.Integer(validate=Range(min=0), missing=1000)
    offset = fields.Integer(validate=Range(min=0), missing=None)
    search = fields.String(missing=None)
    call_direction = fields.String(
        validate=OneOf(['internal', 'inbound', 'outbound']), missing=None
    )
    number = fields.String(validate=Regexp(NUMBER_REGEX), missing=None)
    tags = fields.List(fields.String(), missing=[])
    user_uuid = fields.List(fields.String(), missing=[], attribute='user_uuids')
    from_id = fields.Integer(validate=Range(min=0), attribute='start_id', missing=None)
    recurse = fields.Boolean(missing=False)

    @pre_load
    def convert_tags_and_user_uuid_to_list(self, data):
        result = data.to_dict()
        if data.get('tags'):
            result['tags'] = data['tags'].split(',')
        if data.get('user_uuid'):
            result['user_uuid'] = data['user_uuid'].split(',')
        return result

    @post_load
    def map_order_field(self, in_data):
        mapped_order = CDRSchema().fields[in_data['order']].attribute
        if mapped_order:
            in_data['order'] = mapped_order
        return in_data


class CDRSchemaList(Schema):
    class Meta(object):
        ordered = True

    items = fields.Nested(CDRSchema, many=True)
    total = fields.Integer()
    filtered = fields.Integer()
