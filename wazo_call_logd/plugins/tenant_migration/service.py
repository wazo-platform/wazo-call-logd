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


logger = logging.getLogger(__name__)

TO_MIGRATE_TENANT_UUID = '00000000-0000-0000-0000-000000000000'
CONTEXT_ATTRIBUTES = (
    'requested_context',
    'source_internal_context',
    'destination_internal_context'
    'requested_internal_context',
)


class CallLogdTenantUpgradeService(object):

    def __init__(self, config):
        engine = create_engine(config['db_uri'])
        self._Session = scoped_session(sessionmaker())
        self._Session.configure(bind=engine)
        self._service_tenant_uuid = None

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

    def set_default_tenant_uuid(self, token):
        self._service_tenant_uuid = token["metadata"]["tenant_uuid"]

    def update_contexts(self, context, tenant_uuid):
        with self.rw_session() as session:
            for field in CONTEXT_ATTRIBUTES:
                query = session.query(CallLog)
                query = query.filter(CallLog.tenant_uuid == TO_MIGRATE_TENANT_UUID)
                query = query.filter(CallLog.requested_context == context)
                query.update({CallLog.tenant_uuid: tenant_uuid})

    def update_remaining_call_logs(self):
        with self.rw_session() as session:
            query = session.query(CallLog)
            query = query.filter(CallLog.tenant_uuid == TO_MIGRATE_TENANT_UUID)
            query.update({CallLog.tenant_uuid: self._service_tenant_uuid})
