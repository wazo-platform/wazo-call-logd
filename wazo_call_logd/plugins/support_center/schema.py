# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
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


class QueueStatisticsSchema(Schema):
    class Meta(object):
        ordered = True
        unknown = EXCLUDE

    from_ = fields.String(attribute='from')
    until = fields.String()
    tenant_uuid = fields.UUID()
    queue_id = fields.Integer()
    queue_name = fields.String()
    received = fields.Integer()
    answered = fields.Integer()
    abandoned = fields.Integer()
    closed = fields.Integer()
    not_answered = fields.Integer()
    saturated = fields.Integer()
    blocked = fields.Integer()
    average_waiting_time = fields.Integer()
    answered_rate = fields.Float()
    quality_of_service = fields.Float()


class QueueStatisticsListRequestSchema(Schema):
    from_ = fields.DateTime(data_key='from', missing=None)
    until = fields.DateTime(missing=None)
    interval = fields.String(validate=OneOf(['hour', 'day', 'month']))
    qos_threshold = fields.Integer()
    day_start_time = fields.String(attribute='start_time')  # TODO(afournier): validate Regex?
    day_end_time = fields.String(attribute='end_time')  # TODO(afournier): validate Regex?
    week_days = fields.List(fields.Integer(), missing=[1, 2, 3, 4, 5, 6, 7])

    @pre_load
    def convert_week_days_to_list(self, data):
        result = data.to_dict()
        if data.get('week_days'):
            result['week_days'] = data['week_days'].split(',')
        return result


class QueueStatisticsSchemaList(Schema):
    class Meta(object):
        ordered = True

    items = fields.Nested(QueueStatisticsSchema, many=True)
    total = fields.Integer()
