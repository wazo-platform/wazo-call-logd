# Copyright 2017-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import EXCLUDE, post_dump, post_load, pre_dump, pre_load
from xivo.mallow import fields
from xivo.mallow.validate import Length, OneOf, Range, Regexp
from xivo.mallow_helpers import Schema

NUMBER_REGEX = r'^_?[0-9]+_?$'
CONVERSATION_ID_REGEX = r'^[0-9]+\.[0-9]+$'


class RecordingSchema(Schema):
    uuid = fields.UUID()
    start_time = fields.DateTime()
    end_time = fields.DateTime()
    deleted = fields.Boolean()
    filename = fields.String()
    conversation_id = fields.String()


class RecordingMediaDeleteRequestSchema(Schema):
    cdr_ids = fields.List(fields.Integer(), validate=Length(min=1), required=True)


class CDRListingBase(Schema):
    from_ = fields.DateTime(data_key='from', attribute='start', load_default=None)
    until = fields.DateTime(attribute='end', load_default=None)
    search = fields.String(load_default=None)
    call_direction = fields.String(
        validate=OneOf(['internal', 'inbound', 'outbound']), load_default=None
    )
    number = fields.String(validate=Regexp(NUMBER_REGEX), load_default=None)
    tags = fields.List(fields.String(), load_default=[])
    user_uuid = fields.List(fields.String(), load_default=[], attribute='user_uuids')
    from_id = fields.Integer(
        validate=Range(min=0), attribute='start_id', load_default=None
    )
    recurse = fields.Boolean(load_default=False)

    @pre_load
    def convert_tags_and_user_uuid_to_list(self, data, **kwargs):
        result = data.to_dict()
        if data.get('tags'):
            result['tags'] = data['tags'].split(',')
        if data.get('user_uuid'):
            result['user_uuid'] = data['user_uuid'].split(',')
        return result


class RecordingMediaExportRequestSchema(CDRListingBase):
    email = fields.Email(load_default=None)


class RecordingMediaExportBodySchema(Schema):
    cdr_ids = fields.List(fields.Integer(), load_default=None)


class RecordingMediaExportSchema(Schema):
    uuid = fields.UUID()


class BaseDestinationDetailsSchema(Schema):
    type = fields.String(required=True, dump_default='unknown')


class DestinationConferenceDetails(BaseDestinationDetailsSchema):
    conference_id = fields.Integer()


class DestinationMeetingDetails(BaseDestinationDetailsSchema):
    meeting_uuid = fields.UUID()
    meeting_name = fields.String()


class DestinationUnknownDetails(BaseDestinationDetailsSchema):
    pass


class DestinationUserDetails(BaseDestinationDetailsSchema):
    user_uuid = fields.UUID()
    user_name = fields.String()


class DestinationGroupDetails(BaseDestinationDetailsSchema):
    group_label = fields.String()
    group_id = fields.Integer()


class DestinationQueueDetails(BaseDestinationDetailsSchema):
    queue_name = fields.String()
    queue_id = fields.Integer()


class DestinationDetailsField(fields.Nested):
    destination_details_schemas = {
        'conference': DestinationConferenceDetails,
        'meeting': DestinationMeetingDetails,
        'user': DestinationUserDetails,
        'unknown': DestinationUnknownDetails,
        'group': DestinationGroupDetails,
        'queue': DestinationQueueDetails,
    }

    def __init__(self, *args, **kwargs):
        kwargs['unknown'] = EXCLUDE
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        self.schema.context = self.context
        base = super()._deserialize(value, attr, data, **kwargs)
        return fields.Nested(
            self.destination_details_schemas[base['type']], unknown=self.unknown
        )._deserialize(value, attr, data, **kwargs)

    def _serialize(self, nested_obj, attr, obj):
        base = super()._serialize(nested_obj, attr, obj)
        return fields.Nested(
            self.destination_details_schemas[base['type']], unknown=self.unknown
        )._serialize(nested_obj, attr, obj)


class CDRSchema(Schema):
    id = fields.Integer()
    tenant_uuid = fields.UUID()
    start = fields.DateTime(attribute='date')
    end = fields.DateTime(attribute='date_end')
    answered = fields.Boolean(attribute='marshmallow_answered')
    answer = fields.DateTime(attribute='date_answer')
    duration = fields.TimeDelta(dump_default=None, attribute='marshmallow_duration')
    call_direction = fields.String(attribute='direction')
    conversation_id = fields.String()
    destination_details = DestinationDetailsField(
        BaseDestinationDetailsSchema,
        attribute='destination_details_dict',
        required=True,
    )
    destination_extension = fields.String(attribute='destination_exten')
    destination_internal_context = fields.String()
    destination_internal_extension = fields.String(
        attribute='destination_internal_exten'
    )
    destination_line_id = fields.Integer()
    destination_name = fields.String()
    destination_user_uuid = fields.UUID()
    requested_name = fields.String()
    requested_context = fields.String()
    requested_extension = fields.String(attribute='requested_exten')
    requested_internal_context = fields.String()
    requested_internal_extension = fields.String(attribute='requested_internal_exten')
    requested_user_uuid = fields.UUID()
    source_extension = fields.String(attribute='source_exten')
    source_internal_context = fields.String()
    source_internal_name = fields.String()
    source_internal_extension = fields.String(attribute='source_internal_exten')
    source_line_id = fields.Integer()
    source_name = fields.String()
    source_user_uuid = fields.UUID()
    tags = fields.List(fields.String(), attribute='marshmallow_tags')
    recordings = fields.Nested(
        'RecordingSchema', many=True, dump_default=[], exclude=('conversation_id',)
    )

    @pre_dump
    def _compute_fields(self, data, **kwargs):
        data.marshmallow_answered = True if data.date_answer else False
        if data.date_answer and data.date_end:
            data.marshmallow_duration = data.date_end - data.date_answer
        return data

    @post_dump
    def fix_negative_duration(self, data, **kwargs):
        if data['duration'] is not None:
            data['duration'] = max(data['duration'], 0)
        return data

    @pre_dump
    def _populate_tags_field(self, data, **kwargs):
        data.marshmallow_tags = set()
        for participant in data.participants:
            data.marshmallow_tags.update(participant.tags)
        return data


class CDRListRequestSchema(CDRListingBase):
    direction = fields.String(validate=OneOf(['asc', 'desc']), load_default='desc')
    order = fields.String(
        validate=OneOf(set(CDRSchema().fields) - {'end', 'tags', 'recordings'}),
        load_default='start',
    )
    limit = fields.Integer(validate=Range(min=0), load_default=1000)
    offset = fields.Integer(validate=Range(min=0), load_default=None)
    distinct = fields.String(validate=OneOf(['peer_exten']), load_default=None)
    recorded = fields.Boolean(load_default=None)
    format = fields.String(validate=OneOf(['csv', 'json']), load_default=None)
    conversation_id = fields.String(
        validate=Regexp(
            CONVERSATION_ID_REGEX, error='not a valid conversation identifier'
        ),
        load_default=None,
    )

    @post_load
    def map_order_field(self, in_data, **kwargs):
        mapped_order = CDRSchema().fields[in_data['order']].attribute
        if mapped_order:
            in_data['order'] = mapped_order
        return in_data


class CDRSchemaList(Schema):
    items = fields.Nested(CDRSchema, many=True)
    total = fields.Integer()
    filtered = fields.Integer()
