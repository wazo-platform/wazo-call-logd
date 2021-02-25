# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime

from sqlalchemy import func

from .database.models import CallLog


class CallLogsPurger:
    def purge(self, days_to_keep, session):
        query = CallLog.__table__.delete().where(
            CallLog.date < (func.now() - datetime.timedelta(days=days_to_keep))
        )
        session.execute(query)
