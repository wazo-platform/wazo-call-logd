# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import timedelta as td
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    empty,
    has_property,
    has_properties,
)
from mock import Mock
from xivo_dao.alchemy.cel import CEL

from .helpers.base import DBIntegrationTest
from .helpers.constants import NOW
from .helpers.database import cel


class TestCEL(DBIntegrationTest):
    @cel(linkedid='1')
    def test_associate_when_no_call_logs(self, cel):
        call_logs = []
        self.dao.cel.associate_all_to_call_logs(call_logs)
        result = self.cel_session.query(CEL).filter(CEL.id == cel['id']).first()
        assert_that(result, has_properties(call_log_id=None))

    @cel(linkedid='1')
    def test_associate_when_no_cel_ids(self, cel):
        call_logs = [Mock(cel_ids=[])]
        self.dao.cel.associate_all_to_call_logs(call_logs)
        result = self.cel_session.query(CEL).filter(CEL.id == cel['id']).first()
        assert_that(result, has_properties(call_log_id=None))

    @cel(linkedid='1')
    @cel(linkedid='1')
    def test_associate_many_cels(self, cel1, cel2):
        call_log_id = 1234
        call_logs = [Mock(id=call_log_id, cel_ids=[cel1['id'], cel2['id']])]
        self.dao.cel.associate_all_to_call_logs(call_logs)
        result = self.cel_session.query(CEL).filter(CEL.linkedid == '1').all()
        assert_that(
            result,
            contains_inanyorder(
                has_properties(call_log_id=call_log_id),
                has_properties(call_log_id=call_log_id),
            ),
        )

    @cel(linkedid='1')
    @cel(linkedid='2')
    def test_associate_many_call_logs(self, cel1, cel2):
        call_log_id_1 = 1234
        call_log_id_2 = 5678
        call_logs = [
            Mock(id=call_log_id_1, cel_ids=[cel1['id']]),
            Mock(id=call_log_id_2, cel_ids=[cel2['id']]),
        ]
        self.dao.cel.associate_all_to_call_logs(call_logs)
        cels = [cel1['id'], cel2['id']]
        result = self.cel_session.query(CEL).filter(CEL.id.in_(cels)).all()
        assert_that(
            result,
            contains_inanyorder(
                has_properties(call_log_id=call_log_id_1),
                has_properties(call_log_id=call_log_id_2),
            ),
        )

    def test_find_last_unprocessed_no_cels(self):
        result = self.dao.cel.find_last_unprocessed()

        assert_that(result, empty())

    @cel(linkedid='1')
    @cel(linkedid='2')
    @cel(linkedid='3')
    def test_find_last_unprocessed_over_limit(self, _, cel2, cel3):
        result = self.dao.cel.find_last_unprocessed(limit=2)
        assert_that(
            result,
            contains(
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
            ),
        )

    @cel(linkedid='1')
    @cel(linkedid='2')
    def test_find_last_unprocessed_under_limit(self, cel1, cel2):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            ),
        )

    @cel(linkedid='1')
    @cel(linkedid='1')
    def test_find_last_unprocessed_under_limit_exceeding_limit_to_complete_call(
        self, cel1, cel2
    ):
        result = self.dao.cel.find_last_unprocessed(limit=1)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            ),
        )

    @cel(linkedid='1', processed=True)
    @cel(linkedid='1')
    @cel(linkedid='2', processed=True)
    @cel(linkedid='2')
    def test_find_last_unprocessed_under_limit_exceeding_limit_to_reprocess_partially_processed_call(
        self, cel1, cel2, cel3, cel4
    ):
        result = self.dao.cel.find_last_unprocessed(limit=2)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
                has_property('id', cel4['id']),
            ),
        )

    @cel(processed=True)
    @cel(processed=True)
    def test_find_last_unprocessed_with_only_processed(self, *_):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(result, empty())

    @cel(linkedid='1', processed=True)
    @cel(linkedid='1', processed=True)
    @cel(linkedid='2')
    @cel(linkedid='2')
    def test_find_last_unprocessed_with_processed_and_unprocessed(
        self, _, __, cel3, cel4
    ):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(
            result,
            contains(
                has_property('id', cel3['id']),
                has_property('id', cel4['id']),
            ),
        )

    @cel(linkedid='1')
    @cel(linkedid='1', processed=True)
    @cel(linkedid='2', processed=True)
    @cel(linkedid='2')
    def test_find_last_unprocessed_with_partially_processed(
        self, cel1, cel2, cel3, cel4
    ):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
                has_property('id', cel4['id']),
            ),
        )

    def test_find_from_linked_id_no_cels(self):
        result = self.dao.cel.find_from_linked_id('666')
        assert_that(result, empty())

    @cel(linkedid='666')
    @cel(linkedid='2')
    @cel(linkedid='666')
    def test_find_from_linked_id(self, cel1, _, cel3):
        result = self.dao.cel.find_from_linked_id('666')
        assert_that(
            result,
            contains_inanyorder(
                has_property('id', cel1['id']),
                has_property('id', cel3['id']),
            ),
        )

    @cel(linkedid='666', eventtime=NOW)
    @cel(linkedid='666', eventtime=NOW - td(hours=1))
    @cel(linkedid='666', eventtime=NOW + td(hours=1))
    def test_find_from_linked_id_when_cels_are_unordered_then_return_cels_in_chronological_order(
        self, cel1, cel2, cel3
    ):
        result = self.dao.cel.find_from_linked_id('666')
        assert_that(
            result,
            contains(
                has_property('id', cel2['id']),
                has_property('id', cel1['id']),
                has_property('id', cel3['id']),
            ),
        )

    def test_find_last_unprocessed_no_cels_with_older(self):
        older = NOW - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(result, empty())

    @cel(eventtime=NOW - td(hours=2))  # excluded
    @cel(linkedid='2')
    @cel(linkedid='3')
    def test_find_last_unprocessed_over_older(self, _, cel2, cel3):
        older = NOW - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
            ),
        )

    @cel(linkedid='1')
    @cel(linkedid='2')
    def test_find_last_unprocessed_under_older(self, cel1, cel2):
        older = NOW - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            ),
        )

    @cel(linkedid='1', eventtime=NOW - td(hours=2))
    @cel(linkedid='1')
    def test_find_last_unprocessed_under_older_exceeding_limit_to_complete_call(
        self, cel1, cel2
    ):
        older = NOW - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            ),
        )
