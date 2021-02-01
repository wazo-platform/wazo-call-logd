# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class CDRService:
    def __init__(self, dao):
        self._dao = dao

    def list(self, search_params):
        call_logs = self._dao.call_log.find_all_in_period(search_params)
        ids = [call_log.id for call_log in call_logs]
        recordings = self._dao.recording.find_all_by_call_log_ids(ids)
        if recordings:
            rec_by_id = {}
            for recording in recordings:
                rec_by_id.setdefault(recording.call_log_id, []).append(recording)
            for call_log in call_logs:
                call_log.recordings = rec_by_id.get(call_log.id, [])
        count = self._dao.call_log.count_in_period(search_params)
        return {
            'items': call_logs,
            'filtered': count['filtered'],
            'total': count['total'],
        }

    def get(self, cdr_id, tenant_uuids):
        call_log = self._dao.call_log.get_by_id(cdr_id, tenant_uuids)
        if not call_log:
            return
        recordings = self._dao.recording.find_all_by_call_log_id(call_log.id)
        call_log.recordings = recordings
        return call_log
