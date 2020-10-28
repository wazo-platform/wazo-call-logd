# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .agent_stat import AgentStatDAO
from .call_log import CallLogDAO
from .queue_stat import QueueStatDAO


class DAO:

    _daos = {
        'call_log': CallLogDAO,
        'queue_stat': QueueStatDAO,
        'agent_stat': AgentStatDAO,
    }

    def __init__(self, session):
        for name, dao in self._daos.items():
            setattr(self, name, dao(session))
