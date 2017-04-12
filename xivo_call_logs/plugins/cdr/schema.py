# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow.decorators import pre_dump
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


cdr_schema = CDRSchema()
