# Copyright 2013-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dao.resources.call_log import dao as call_log_dao


class CallLogsWriter(object):

    def write(self, call_logs_creation):
        call_log_dao.delete_from_list(call_logs_creation.call_logs_to_delete)
        call_log_dao.create_from_list(call_logs_creation.new_call_logs)
