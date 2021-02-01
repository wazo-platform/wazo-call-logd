# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import BaseDAO
from ..models import Recording


class RecordingDAO(BaseDAO):
    def create_all(self, recordings):
        with self.new_session() as session:
            for recording in recordings:
                session.add(recording)
                session.flush()
                session.expunge(recording)

    def delete_all(self):
        with self.new_session() as session:
            session.query(Recording).delete()
            session.flush()

    def delete_all_by_call_log_ids(self, call_log_ids):
        if not call_log_ids:
            return
        with self.new_session() as session:
            filter_ = Recording.call_log_id.in_(call_log_ids)
            query = session.query(Recording).filter(filter_)
            query.delete(synchronize_session='fetch')
            session.flush()

    def find_all_by_call_log_ids(self, call_log_ids):
        if not call_log_ids:
            return
        with self.new_session() as session:
            filter_ = Recording.call_log_id.in_(call_log_ids)
            query = session.query(Recording).filter(filter_)
            recordings = query.all()
            for recording in recordings:
                session.expunge(recording)
            return recordings

    def find_all_by_call_log_id(self, call_log_id):
        with self.new_session() as session:
            filter_ = Recording.call_log_id == call_log_id
            query = session.query(Recording).filter(filter_)
            recordings = query.all()
            for recording in recordings:
                session.expunge(recording)
            return recordings
