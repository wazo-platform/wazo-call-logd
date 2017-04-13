# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import Schema, fields


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
    from_ = fields.DateTime(load_from='from')
    until = fields.DateTime()


cdr_schema = CDRSchema()
list_schema = CDRListRequestSchema(strict=True)
