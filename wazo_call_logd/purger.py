# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime

from sqlalchemy import func

from .database.models import CallLog, Retention, Tenant


class CallLogsPurger:
    def purge(self, days_to_keep, session):
        retentions = {r.tenant_uuid: r for r in session.query(Retention).all()}
        tenants = session.query(Tenant).all()
        for tenant in tenants:
            days = days_to_keep
            retention = retentions.get(tenant.uuid)
            if retention and retention.cdr_days is not None:
                days = retention.cdr_days

            max_date = func.now() - datetime.timedelta(days=days)
            query = (
                session.query(CallLog)
                .filter(CallLog.date < max_date)
                .filter(CallLog.tenant_uuid == tenant.uuid)
            )
            query.delete(synchronize_session=False)
