# Copyright 2013-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timedelta as td,
)
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    empty,
    has_property,
)

from .helpers.base import DBIntegrationTest
from .helpers.database import cel


class TestCEL(DBIntegrationTest):
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
            )
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
            )
        )

    @cel(linkedid='1')
    @cel(linkedid='1')
    def test_find_last_unprocessed_under_limit_exceeding_limit_to_complete_call(self, cel1, cel2):
        result = self.dao.cel.find_last_unprocessed(limit=1)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            )
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
            )
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
    def test_find_last_unprocessed_with_processed_and_unprocessed(self, _, __, cel3, cel4):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(
            result,
            contains(
                has_property('id', cel3['id']),
                has_property('id', cel4['id']),
            )
        )

    @cel(linkedid='1')
    @cel(linkedid='1', processed=True)
    @cel(linkedid='2', processed=True)
    @cel(linkedid='2')
    def test_find_last_unprocessed_with_partially_processed(self, cel1, cel2, cel3, cel4):
        result = self.dao.cel.find_last_unprocessed(limit=10)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
                has_property('id', cel4['id']),
            )
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
            )
        )

    @cel(linkedid='666', eventtime=dt.now())
    @cel(linkedid='666', eventtime=dt.now() - td(hours=1))
    @cel(linkedid='666', eventtime=dt.now() + td(hours=1))
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
            )
        )

    def test_find_last_unprocessed_no_cels_with_older(self):
        older = dt.now() - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(result, empty())

    @cel(eventtime=dt.now() - td(hours=2))  # excluded
    @cel(linkedid='2')
    @cel(linkedid='3')
    def test_find_last_unprocessed_over_older(self, _, cel2, cel3):
        older = dt.now() - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel2['id']),
                has_property('id', cel3['id']),
            )
        )

    @cel(linkedid='1')
    @cel(linkedid='2')
    def test_find_last_unprocessed_under_older(self, cel1, cel2):
        older = dt.now() - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            )
        )

    @cel(linkedid='1', eventtime=dt.now() - td(hours=2))
    @cel(linkedid='1')
    def test_find_last_unprocessed_under_older_exceeding_limit_to_complete_call(
        self, cel1, cel2,
    ):
        older = dt.now() - td(hours=1)
        result = self.dao.cel.find_last_unprocessed(older=older)
        assert_that(
            result,
            contains(
                has_property('id', cel1['id']),
                has_property('id', cel2['id']),
            )
        )
