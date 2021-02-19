# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import BaseDAO
from ..models import Recording


class _UselessQuery(Exception):
    pass


class RecordingDAO(BaseDAO):
    def create_all(self, recordings):
        with self.new_session() as session:
            for recording in recordings:
                session.add(recording)
                session.flush()
                session.expunge(recording)

    def delete_media_by(self, **kwargs):
        with self.new_session() as session:
            query = session.query(Recording)
            try:
                query = self._apply_filters(query, kwargs)
            except _UselessQuery:
                return

            recordings = query.all()
            for recording in recordings:
                recording.path = None
                session.flush()
                session.expunge(recording)

    def find_all_by(self, **kwargs):
        with self.new_session() as session:
            query = session.query(Recording)
            try:
                query = self._apply_filters(query, kwargs)
            except _UselessQuery:
                return []

            recordings = query.all()
            for recording in recordings:
                session.expunge(recording)
            return recordings

    def find_by(self, **kwargs):
        with self.new_session() as session:
            query = session.query(Recording)
            try:
                query = self._apply_filters(query, kwargs)
            except _UselessQuery:
                return

            recording = query.first()
            if not recording:
                return
            session.expunge(recording)
            return recording

    def _apply_filters(self, query, params):
        if 'call_log_ids' in params:
            if not params['call_log_ids']:
                raise _UselessQuery()
            query = query.filter(Recording.call_log_id.in_(params['call_log_ids']))

        if 'call_log_id' in params:
            query = query.filter(Recording.call_log_id == params['call_log_id'])

        if 'uuid' in params:
            query = query.filter(Recording.uuid == params['uuid'])

        return query
