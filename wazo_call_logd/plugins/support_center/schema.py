# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import (
    fields,
    post_load,
    pre_load,
    validates_schema,
    ValidationError,
)
from datetime import timezone, time
from marshmallow.validate import OneOf, ContainsOnly, Range, Regexp
from xivo.mallow_helpers import Schema

HOUR_REGEX = r"^([0,1][0-9]|2[0-3]):[0-5][0-9]$"


class QueueStatisticsSchema(Schema):
    from_ = fields.DateTime(attribute='from', data_key='from')
    until = fields.DateTime()
    tenant_uuid = fields.UUID(default=None)
    queue_id = fields.Integer(default=None)
    queue_name = fields.String(default=None)
    received = fields.Integer(attribute='total', default=0)
    answered = fields.Integer(default=0)
    abandoned = fields.Integer(default=0)
    closed = fields.Integer(default=0)
    not_answered = fields.Integer(attribute='timeout', default=0)
    saturated = fields.Integer(default=0)
    blocked = fields.Integer(attribute='blocking', default=0)
    average_waiting_time = fields.Integer(default=0)
    answered_rate = fields.Float(default=0.0)
    quality_of_service = fields.Float(attribute='qos', default=None)


class QueueStatisticsListRequestSchema(Schema):
    from_ = fields.DateTime(data_key='from', missing=None)
    until = fields.DateTime(missing=None)
    qos_threshold = fields.Integer(validate=Range(min=0))
    day_start_time = fields.String(attribute='start_time', validate=Regexp(HOUR_REGEX))
    day_end_time = fields.String(attribute='end_time', validate=Regexp(HOUR_REGEX))
    week_days = fields.List(
        fields.Integer(),
        missing=[1, 2, 3, 4, 5, 6, 7],
        validate=ContainsOnly([1, 2, 3, 4, 5, 6, 7]),
    )

    @pre_load
    def convert_week_days_to_list(self, data):
        result = data.to_dict()
        if data.get('week_days'):
            result['week_days'] = list(set(data['week_days'].split(',')))
        return result

    @post_load
    def convert_time_to_hour(self, data, **kwargs):
        if data.get('start_time'):
            start_time = time.fromisoformat(data['start_time'])
            data['start_time'] = start_time.hour
        if data.get('end_time'):
            end_time = time.fromisoformat(data['end_time'])
            data['end_time'] = end_time.hour
        return data

    @post_load
    def default_timezone_on_datetime(self, data, **kwargs):
        if data.get('from_'):
            if not data['from_'].tzinfo:
                data['from_'] = data['from_'].replace(tzinfo=timezone.utc)
        if data.get('until'):
            if not data['until'].tzinfo:
                data['until'] = data['until'].replace(tzinfo=timezone.utc)
        return data

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data.get('until') and data.get('from_'):
            from_ = data['from_']
            until = data['until']
            if not from_.tzinfo:
                from_ = from_.replace(tzinfo=timezone.utc)
            if not until.tzinfo:
                until = until.replace(tzinfo=timezone.utc)
            if until <= from_:
                raise ValidationError({'until': 'Field must be greater than from'})


class QueueStatisticsRequestSchema(QueueStatisticsListRequestSchema):
    interval = fields.String(validate=OneOf(['hour', 'day', 'month']))


class QueueStatisticsSchemaList(Schema):
    items = fields.Nested(QueueStatisticsSchema, many=True)
    total = fields.Integer()
