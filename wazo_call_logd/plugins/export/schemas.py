# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow_helpers import Schema


class ExportSchema(Schema):
    uuid = fields.UUID()
    tenant_uuid = fields.UUID()
    user_uuid = fields.UUID()
    date = fields.DateTime()
    filename = fields.String()
    status = fields.String()
