# Copyright 2013-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import namedtuple
from itertools import groupby
from operator import attrgetter
from wazo_call_logd.exceptions import InvalidCallLogException
from wazo_call_logd import raw_call_log


logger = logging.getLogger(__name__)
CallLogsCreation = namedtuple('CallLogsCreation', ('new_call_logs', 'call_logs_to_delete'))


class CallLogsGenerator(object):

    def __init__(self, cel_interpretors):
        self._cel_interpretors = cel_interpretors

    def from_cel(self, cels):
        call_logs_to_delete = self.list_call_log_ids(cels)
        new_call_logs = self.call_logs_from_cel(cels)
        return CallLogsCreation(new_call_logs=new_call_logs, call_logs_to_delete=call_logs_to_delete)

    def call_logs_from_cel(self, cels):
        result = []
        for _, cels_by_call_iter in self._group_cels_by_linkedid(cels):
            cels_by_call = list(cels_by_call_iter)

            call_log = raw_call_log.RawCallLog()
            call_log.cel_ids = [cel.id for cel in cels_by_call]

            interpretor = self._get_interpretor(cels_by_call)
            call_log = interpretor.interpret_cels(cels_by_call, call_log)

            self._tenant_checker(call_log)

            try:
                result.append(call_log.to_call_log())
            except InvalidCallLogException as e:
                logger.debug('Invalid call log detected: %s', e)

        return result

    def list_call_log_ids(self, cels):
        return set(cel.call_log_id for cel in cels if cel.call_log_id)

    def _group_cels_by_linkedid(self, cels):
        cels = sorted(cels, key=attrgetter('linkedid'))
        return groupby(cels, key=attrgetter('linkedid'))

    def _get_interpretor(self, cels):
        for interpretor in self._cel_interpretors:
            if interpretor.can_interpret(cels):
                return interpretor

        raise RuntimeError('Could not find suitable interpretor in {}'.format(self._cel_interpretors))

    @staticmethod
    def _tenant_checker(call_log):
        for prefix in ('requested', 'requested_internal',
                       'source_internal', 'destination_internal'):
            if getattr(call_log, '%s_tenant_uuid' % prefix):
                return
        for participant in call_log.participants:
            if participant.tenant_uuid:
                return

        logger.warning("call log of cels `%s` is not attached to a "
                       "tenant_uuid", call_log.cel_ids)
