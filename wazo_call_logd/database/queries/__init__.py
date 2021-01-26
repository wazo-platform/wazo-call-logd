# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .agent_stat import AgentStatDAO
from .call_log import CallLogDAO
from .queue_stat import QueueStatDAO


class DAO:

    _dao = {}
    _cel_dao = {
        'call_log': CallLogDAO,
        'queue_stat': QueueStatDAO,
        'agent_stat': AgentStatDAO,
    }

    def __init__(self, session, cel_db_session):
        for name, dao in self._dao.items():
            setattr(self, name, dao(session))
        for name, dao in self._cel_dao.items():
            setattr(self, name, dao(cel_db_session))
