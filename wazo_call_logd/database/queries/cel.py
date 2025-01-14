# Copyright 2013-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_dao.alchemy.cel import CEL

from .base import BaseDAO


def eject(session, objects):
    for obj in objects:
        session.expunge(obj)
    return objects


class CELDAO(BaseDAO):
    def associate_all_to_call_logs(self, call_logs):
        with self.new_session() as session:
            for call_log in call_logs:
                if not call_log.cel_ids:
                    continue
                query = session.query(CEL).filter(CEL.id.in_(call_log.cel_ids))
                query.update({'call_log_id': call_log.id}, synchronize_session=False)

    def unassociate_all_from_call_log_ids(self, call_log_ids):
        if not call_log_ids:
            return

        with self.new_session() as session:
            query = session.query(CEL).filter(CEL.call_log_id.in_(call_log_ids))
            query.update({'call_log_id': None}, synchronize_session=False)

    def unassociate_all(self):
        with self.new_session() as session:
            query = session.query(CEL)
            query.update({'call_log_id': None}, synchronize_session=False)

    def _correlated_cels_by_uniqueid(self, session, base_cels):
        unique_ids = {row.uniqueid for row in base_cels.all()}
        correlated_linkedids = {
            row.linkedid
            for row in session.query(CEL.linkedid)
            .distinct(CEL.linkedid)
            .filter(CEL.uniqueid.in_(unique_ids))
            .all()
        }
        correlated_cels = (
            session.query(CEL)
            .filter(CEL.linkedid.in_(correlated_linkedids))
            .order_by(CEL.eventtime.asc())
        )

        return correlated_cels

    def find_last_unprocessed(self, limit=None, older=None):
        with self.new_session() as session:
            subquery = (
                session.query(CEL.uniqueid)
                .filter(CEL.call_log_id.is_(None))
                .filter(CEL.channame != 'Message/ast_msg_queue')  # ignore SIP chat
                .order_by(CEL.eventtime.desc())
            )

            if limit:
                subquery = subquery.limit(limit)
            elif older:
                subquery = subquery.filter(CEL.eventtime >= older)

            cels = list(self._correlated_cels_by_uniqueid(session, subquery))
            return eject(session, cels)

    def find_from_linked_id(self, linked_id):
        with self.new_session() as session:
            linked_cels = (
                session.query(CEL.uniqueid)
                .distinct(CEL.uniqueid)
                .filter(CEL.linkedid == linked_id)
            )
            correlated_cels = list(
                self._correlated_cels_by_uniqueid(session, linked_cels)
            )
            return eject(session, correlated_cels)
