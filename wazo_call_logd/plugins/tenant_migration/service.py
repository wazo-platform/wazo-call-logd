# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import contextlib
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker
)
from xivo_dao.alchemy.call_log import CallLog
from xivo_dao.alchemy.call_log_participant import CallLogParticipant


logger = logging.getLogger(__name__)

TO_MIGRATE_TENANT_UUID = '00000000-0000-0000-0000-000000000000'


class CallLogdTenantUpgradeService(object):

    def __init__(self, config):
        engine = create_engine(config['db_uri'])
        self._Session = scoped_session(sessionmaker())
        self._Session.configure(bind=engine)

    @contextlib.contextmanager
    def rw_session(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def update_participants(self, user_uuid, tenant_uuid):
        logger.info('updating user(%s) tenant to %s', user_uuid, tenant_uuid)
        with self.rw_session() as session:
            query = session.query(CallLogParticipant)
            query = query.filter(CallLogParticipant.tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query = query.filter(CallLogParticipant.user_uuid == user_uuid)
            query.update({CallLogParticipant.tenant_uuid: tenant_uuid})

    def update_contexts(self, context, tenant_uuid):
        with self.rw_session() as session:
            query = session.query(CallLog)
            query = query.filter(CallLog.requested_tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query = query.filter(CallLog.requested_context == context)
            query.update({CallLog.requested_tenant_uuid: tenant_uuid})

            query = session.query(CallLog)
            query = query.filter(CallLog.requested_internal_tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query = query.filter(CallLog.requested_internal_context == context)
            query.update({CallLog.requested_internal_tenant_uuid: tenant_uuid})

            query = session.query(CallLog)
            query = query.filter(CallLog.source_internal_tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query = query.filter(CallLog.source_internal_context == context)
            query.update({CallLog.source_internal_tenant_uuid: tenant_uuid})

            query = session.query(CallLog)
            query = query.filter(CallLog.destination_internal_tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query = query.filter(CallLog.destination_internal_context == context)
            query.update({CallLog.destination_internal_tenant_uuid: tenant_uuid})
