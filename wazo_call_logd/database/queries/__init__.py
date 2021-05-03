# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .agent_stat import AgentStatDAO
from .call_log import CallLogDAO
from .cel import CELDAO
from .queue_stat import QueueStatDAO
from .recording import RecordingDAO
from .retention import RetentionDAO
from .tenant import TenantDAO


class DAO:

    _dao = {
        'call_log': CallLogDAO,
        'recording': RecordingDAO,
        'retention': RetentionDAO,
        'tenant': TenantDAO,
    }
    _cel_dao = {
        'cel': CELDAO,
        'queue_stat': QueueStatDAO,
        'agent_stat': AgentStatDAO,
    }

    def __init__(self, session, cel_db_session):
        for name, dao in self._dao.items():
            setattr(self, name, dao(session))
        for name, dao in self._cel_dao.items():
            setattr(self, name, dao(cel_db_session))
