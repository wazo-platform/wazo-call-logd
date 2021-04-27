# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import datetime
import logging

from sqlalchemy import func

from .database.models import (
    CallLog,
    Recording,
    Retention,
    Tenant,
)

logger = logging.getLogger(__name__)


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


class RecordingsPurger:
    def purge(self, days_to_keep, session):
        retentions = {r.tenant_uuid: r for r in session.query(Retention).all()}
        tenants = session.query(Tenant).all()
        for tenant in tenants:
            days = days_to_keep
            retention = retentions.get(tenant.uuid)
            if retention and retention.recording_days is not None:
                days = retention.recording_days

            max_date = func.now() - datetime.timedelta(days=days)
            query = (
                session.query(CallLog)
                .join(Recording, Recording.call_log_id == CallLog.id)
                .filter(CallLog.date < max_date)
                .filter(CallLog.tenant_uuid == tenant.uuid)
            )

            for cdr in query.all():
                for recording in cdr.recordings:
                    if recording.path:
                        try:
                            # NOTE(fblackburn): wazo-purge-db must be executed
                            # on the same filesystem than wazo-call-logd
                            os.remove(recording.path)
                        except FileNotFoundError:
                            logger.info(
                                'Recording file already deleted: "%s". Marking as such.',
                                recording.path,
                            )

            subquery = (
                session.query(CallLog.id)
                .filter(CallLog.date < max_date)
                .filter(CallLog.tenant_uuid == tenant.uuid)
            )
            query = session.query(Recording).filter(Recording.call_log_id.in_(subquery))
            query.update({'path': None}, synchronize_session=False)
