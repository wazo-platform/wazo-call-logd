# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from marshmallow.validate import Range


class CDRSchema(Schema):
    start = fields.DateTime(attribute='date')
    end = fields.DateTime(attribute='end')
    source_name = fields.String()
    source_extension = fields.String(attribute='source_exten')
    destination_name = fields.String()
    destination_extension = fields.String(attribute='destination_exten')
    duration = fields.TimeDelta()
    answered = fields.Boolean()


class CDRListRequestSchema(Schema):
    from_ = fields.DateTime(load_from='from', missing=None)
    until = fields.DateTime(missing=None)
    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='desc')
    order = fields.String(validate=OneOf(['start']), missing='start')
    limit = fields.Integer(validate=Range(min=0), missing=None)
    offset = fields.Integer(validate=Range(min=0), missing=None)


cdr_schema = CDRSchema()
list_schema = CDRListRequestSchema(strict=True)
