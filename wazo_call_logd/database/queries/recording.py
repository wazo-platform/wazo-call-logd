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

    def delete_all_by_call_log_ids(self, call_log_ids):
        if not call_log_ids:
            return
        with self.new_session() as session:
            query = session.query(Recording).filter(Recording.call_log_id.in_(call_log_ids))
            query.delete(synchronize_session='fetch')
            session.flush()
