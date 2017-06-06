# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import fields
from marshmallow import post_load
from marshmallow import Schema
from marshmallow import pre_dump, pre_load, post_dump
from marshmallow.validate import OneOf
from marshmallow.validate import Range
from marshmallow.validate import Regexp

NUMBER_REGEX = r'^_?[0-9]+_?$'


class CDRSchema(Schema):
    id = fields.Integer()
    start = fields.DateTime(attribute='date')
    answer = fields.DateTime(attribute='date_answer')
    end = fields.DateTime(attribute='date_end')
    source_name = fields.String()
    source_extension = fields.String(attribute='source_exten')
    call_direction = fields.String(attribute='direction')
    destination_name = fields.String()
    destination_extension = fields.String(attribute='destination_exten')
    duration = fields.TimeDelta(default=None, attribute='marshmallow_duration')
    answered = fields.Boolean(attribute='marshmallow_answered')
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
    from_ = fields.DateTime(load_from='from', attribute='start', missing=None)
    until = fields.DateTime(attribute='end', missing=None)
    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='asc')
    order = fields.String(validate=OneOf(set(CDRSchema().fields) - {'end', 'tags'}), missing='start')
    limit = fields.Integer(validate=Range(min=0), missing=None)
    offset = fields.Integer(validate=Range(min=0), missing=None)
    search = fields.String(missing=None)
    call_direction = fields.String(validate=OneOf(['internal', 'inbound', 'outbound']), missing=None)
    number = fields.String(validate=Regexp(NUMBER_REGEX), missing=None)
    tags = fields.List(fields.String(), missing=[])
    user_uuid = fields.List(fields.String(), missing=[], attribute='user_uuids')

    class Meta(object):
        strict = True

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


class CDRSchemaList(Schema):
    items = fields.Nested(CDRSchema, many=True)
    total = fields.Integer()
    filtered = fields.Integer()
