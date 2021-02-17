# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class CallLogsWriter:
    def __init__(self, dao):
        self._dao = dao

    def write(self, call_logs):
        self._dao.call_log.delete_from_list(call_logs.call_logs_to_delete)
        self._dao.recording.delete_all_by_call_log_ids(call_logs.call_logs_to_delete)

        self._dao.call_log.create_from_list(call_logs.new_call_logs)
        self._dao.cel.associate_all_to_call_logs(call_logs.new_call_logs)

        new_recordings = []
        for call_log in call_logs.new_call_logs:
            for recording in call_log.recordings:
                recording.call_log_id = call_log.id
                new_recordings.append(recording)
        self._dao.recording.create_all(new_recordings)
