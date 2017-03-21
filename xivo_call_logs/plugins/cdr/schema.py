# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import Schema, fields


class CDRSchema(Schema):
    start = fields.DateTime()
    source_name = fields.String()
    source_extension = fields.String()
    destination_name = fields.String()
    destination_extension = fields.String()
    duration = fields.Integer()
    answered = fields.Boolean()


cdr_schema = CDRSchema()
