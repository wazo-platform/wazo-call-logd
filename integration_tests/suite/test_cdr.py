# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from contextlib import contextmanager
from hamcrest import assert_that
from hamcrest import calling
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import has_properties
from datetime import timedelta
from xivo_call_logs_client.exceptions import CallLogdError
from xivo_test_helpers.hamcrest.raises import raises

from .test_api.base import IntegrationTest
from .test_api.constants import VALID_TOKEN
from .test_api.hamcrest.contains_string_ignoring_case import contains_string_ignoring_case


class TestNoAuth(IntegrationTest):

    asset = 'base'

    def test_given_no_auth_when_list_cdr_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.cdr.list),
                raises(CallLogdError).matching(has_properties(status_code=503,
                                                              message=contains_string_ignoring_case('auth')))
            )

    def test_given_no_token_when_list_cdr_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list),
            raises(CallLogdError).matching(has_properties(status_code=401,
                                                          message=contains_string_ignoring_case('unauthorized')))
        )
        self.call_logd.set_token(VALID_TOKEN)


class TestListCDR(IntegrationTest):

    asset = 'base'

    def test_given_no_call_logs_when_list_cdr_then_empty_list(self):
        result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=empty(),
                                        filtered=0,
                                        total=0))

    def test_given_call_logs_when_list_cdr_then_list_cdr(self):
        call_logs = [
            {'answered': True,
             'date': '2017-03-23 00:00:00',
             'destination_exten': '3378',
             'destination_name': u'dést.',
             'duration': timedelta(seconds=87),
             'source_exten': '7687',
             'source_name': u'soùr.'},
            {'answered': False,
             'date': '2017-03-23 11:11:11',
             'destination_exten': '8733',
             'destination_name': u'.tsèd',
             'duration': timedelta(seconds=78),
             'source_exten': '7867',
             'source_name': u'.rùos'},
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(answered=True,
                        start='2017-03-23T00:00:00+00:00',
                        end='2017-03-23T00:01:27+00:00',
                        destination_extension='3378',
                        destination_name=u'dést.',
                        duration=87,
                        source_extension='7687',
                        source_name=u'soùr.'),
            has_entries(answered=False,
                        start='2017-03-23T11:11:11+00:00',
                        end='2017-03-23T11:12:29+00:00',
                        destination_extension='8733',
                        destination_name=u'.tsèd',
                        duration=78,
                        source_extension='7867',
                        source_name=u'.rùos'),
        ),
                                        filtered=2,
                                        total=2))

    def test_given_wrong_params_when_list_cdr_then_400(self):
        wrong_params = ('abcd', '12:345', '2017-042-10')
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(from_=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('from'))))
            assert_that(
                calling(self.call_logd.cdr.list).with_args(until=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('until'))))
            assert_that(
                calling(self.call_logd.cdr.list).with_args(direction=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('direction'))))
            assert_that(
                calling(self.call_logd.cdr.list).with_args(order=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('order'))))
            assert_that(
                calling(self.call_logd.cdr.list).with_args(limit=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('limit'))))
            assert_that(
                calling(self.call_logd.cdr.list).with_args(offset=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('offset'))))

    def test_given_call_logs_when_list_cdr_in_range_then_list_cdr_in_range(self):
        call_logs = [
            {'date': '2017-04-10'},
            {'date': '2017-04-11'},
            {'date': '2017-04-12'},
            {'date': '2017-04-13'},
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list(from_='2017-04-11', until='2017-04-13')

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-12T00:00:00+00:00'),
        ),
                                        filtered=2,
                                        total=4))

    def test_given_call_logs_when_list_cdr_in_order_then_list_cdr_in_order(self):
        call_logs = [
            {'date': '2017-04-10'},
            {'date': '2017-04-12'},
            {'date': '2017-04-11'},
        ]

        with self.call_logs(call_logs):
            result_asc = self.call_logd.cdr.list(order='start', direction='asc')
            result_desc = self.call_logd.cdr.list(order='start', direction='desc')

        assert_that(result_asc, has_entry('items', contains(
            has_entries(start='2017-04-10T00:00:00+00:00'),
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-12T00:00:00+00:00'),
        )))

        assert_that(result_desc, has_entry('items', contains(
            has_entries(start='2017-04-12T00:00:00+00:00'),
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-10T00:00:00+00:00'),
        )))

    def test_given_call_logs_when_list_cdr_with_pagination_then_list_cdr_paginated(self):
        call_logs = [
            {'date': '2017-04-10'},
            {'date': '2017-04-12'},
            {'date': '2017-04-11'},
        ]

        with self.call_logs(call_logs):
            result_unpaginated = self.call_logd.cdr.list()
            result_paginated = self.call_logd.cdr.list(limit=1, offset=1)

        assert_that(result_paginated, has_entries(filtered=3,
                                                  total=3,
                                                  items=contains(
            result_unpaginated['items'][1],
        )))

    @contextmanager
    def call_logs(self, call_logs):
        with self.database.queries() as queries:
            for call_log in call_logs:
                call_log['id'] = queries.insert_call_log(**call_log)

        yield

        with self.database.queries() as queries:
            for call_log in call_logs:
                queries.delete_call_log(call_log['id'])
