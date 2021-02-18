# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re

RECORDING_FILENAME_RE = re.compile(r'^.+-(\d+)-([a-z0-9-]{36})(.*)?$')


class CDRService:
    def __init__(self, dao):
        self._dao = dao

    def list(self, search_params):
        searched = search_params.get('search')
        rec_search_params = {}
        if searched:
            matches = RECORDING_FILENAME_RE.search(searched)
            if matches:
                del search_params['search']
                search_params['id'] = matches.group(1)
                rec_search_params['uuid'] = matches.group(2)
        call_logs = self._dao.call_log.find_all_in_period(search_params)
        rec_search_params['call_log_ids'] = [call_log.id for call_log in call_logs]
        recordings = self._dao.recording.find_all_by(**rec_search_params)
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
        recordings = self._dao.recording.find_all_by(call_log_id=call_log.id)
        call_log.recordings = recordings
        return call_log


class RecordingService:
    def __init__(self, dao):
        self._dao = dao

    def find_by(self, **kwargs):
        return self._dao.recording.find_by(**kwargs)

    def find_cdr(self, cdr_id, tenant_uuids):
        return self._dao.call_log.get_by_id(cdr_id, tenant_uuids)

    def delete_media(self, cdr_id, recording_uuid, recording_path):
        self._dao.recording.delete_media_by(call_log_id=cdr_id, uuid=recording_uuid)
        if recording_path:
            os.remove(recording_path)
