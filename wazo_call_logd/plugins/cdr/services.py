# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re
from datetime import datetime
from typing import TypedDict, cast

from wazo_call_logd.database.models import Export
from wazo_call_logd.database.queries import DAO
import wazo_call_logd.database.queries.call_log as call_log_dao
from wazo_call_logd.datatypes import CallDirection, OrderDirection

from .celery_tasks import export_recording_task

RECORDING_FILENAME_RE = re.compile(r'^.+-(\d+)-([a-z0-9-]{36})(.*)?$')


class SearchParams(TypedDict, total=False):
    search: str
    order: str
    direction: OrderDirection
    limit: int
    offset: int
    distinct: str
    start: datetime
    end: datetime
    call_direction: CallDirection
    cdr_ids: list[int]
    number: str
    tags: list[str]
    tenant_uuids: list[str]
    me_user_uuid: str
    user_uuids: list[str]
    recorded: bool


class CDRService:
    def __init__(self, dao):
        self._dao: DAO = dao

    def list(self, search_params: SearchParams):
        searched = search_params.get('search')
        rec_search_params = {}
        dao_params = dict(search_params)
        if searched:
            # check if search param refers to recording
            matches = RECORDING_FILENAME_RE.search(searched)
            if matches:
                del dao_params['search']
                dao_params['id'] = matches.group(1)
                rec_search_params['uuid'] = matches.group(2)
        if user_uuids := search_params.get('user_uuids'):
            # api level 'user_uuids' is reinterpreted to avoid matching hidden participants
            del dao_params['user_uuids']
            dao_params['terminal_user_uuids'] = user_uuids
        call_logs = self._dao.call_log.find_all_in_period(
            cast(call_log_dao.ListParams, dao_params)
        )
        rec_search_params['call_log_ids'] = [call_log.id for call_log in call_logs]
        count = self._dao.call_log.count_in_period(dao_params)
        return {
            'items': call_logs,
            'filtered': count['filtered'],
            'total': count['total'],
        }

    def get(self, cdr_id, tenant_uuids):
        return self._dao.call_log.get_by_id(cdr_id, tenant_uuids)


class RecordingService:
    def __init__(self, dao, config, notifier):
        self._dao = dao
        self._config = config
        self._notifier = notifier

    def find_by(self, **kwargs):
        return self._dao.recording.find_by(**kwargs)

    def delete_media(self, cdr_id, recording_uuid, recording_path):
        self._dao.recording.delete_media_by(call_log_id=cdr_id, uuid=recording_uuid)
        if recording_path:
            os.remove(recording_path)

    def start_recording_export(
        self,
        recordings,
        user_uuid,
        tenant_uuid,
        destination_email,
        connection_info,
    ):
        recording_files = [
            {
                'uuid': recording.uuid,
                'filename': recording.filename,
                'path': recording.path,
                'call_log_id': recording.call_log_id,
            }
            for recording in recordings
        ]

        destination = self._config['exports']['directory']
        export_data = Export(
            user_uuid=user_uuid,
            tenant_uuid=tenant_uuid,
            requested_at=datetime.now(),
            status='pending',
        )
        export = self._dao.export.create(export_data)
        self._notifier.created(export)
        export_recording_task.apply_async(
            args=(
                export.uuid,
                recording_files,
                destination,
                tenant_uuid,
                destination_email,
                connection_info,
            ),
            task_id=str(export.uuid),
        )
        return {'uuid': export.uuid}
