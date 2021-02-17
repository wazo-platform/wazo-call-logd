# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_dao.alchemy.cel import CEL

from .base import BaseDAO


class CELDAO(BaseDAO):
    def associate_all_to_call_logs(self, call_logs):
        with self.new_session() as session:
            for call_log in call_logs:
                if not call_log.cel_ids:
                    continue
                query = session.query(CEL).filter(CEL.id.in_(call_log.cel_ids))
                query.update({'call_log_id': call_log.id}, synchronize_session=False)

    def find_last_unprocessed(self, limit=None, older=None):
        with self.new_session() as session:
            subquery = (
                session
                .query(CEL.linkedid)
                .filter(CEL.call_log_id.is_(None))
                .order_by(CEL.eventtime.desc())
            )
            if limit:
                subquery = subquery.limit(limit)
            elif older:
                subquery = subquery.filter(CEL.eventtime >= older)

            linked_ids = subquery.subquery()

            cel_rows = (
                session
                .query(CEL)
                .filter(CEL.linkedid.in_(linked_ids))
                .order_by(CEL.eventtime.desc())
                .all()
            )
            cel_rows.reverse()
            for cel in cel_rows:
                session.expunge(cel)
            return cel_rows

    def find_from_linked_id(self, linked_id):
        with self.new_session() as session:
            cel_rows = (
                session
                .query(CEL)
                .filter(CEL.linkedid == linked_id)
                .order_by(CEL.eventtime.asc())
                .all()
            )
            for cel in cel_rows:
                session.expunge(cel)
            return cel_rows
