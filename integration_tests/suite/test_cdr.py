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

from .test_api.auth import MockUserToken
from .test_api.base import IntegrationTest
from .test_api.constants import NON_USER_TOKEN
from .test_api.constants import VALID_TOKEN
from .test_api.hamcrest.contains_string_ignoring_case import contains_string_ignoring_case

SOME_USER_UUID = '7a0c6fe6-219d-4977-80e4-1bfc7ab0b289'


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
             'date_answer': '2017-03-23 00:01:00',
             'destination_exten': '3378',
             'destination_name': u'dést.',
             'duration': timedelta(seconds=87),
             'direction': 'internal',
             'source_exten': '7687',
             'source_name': u'soùr.'},
            {'answered': False,
             'date': '2017-03-23 11:11:11',
             'date_answer': '2017-03-23 11:12:11',
             'destination_exten': '8733',
             'destination_name': u'.tsèd',
             'duration': timedelta(seconds=78),
             'direction': 'outbound',
             'source_exten': '7867',
             'source_name': u'.rùos'},
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(answered=True,
                        start='2017-03-23T00:00:00+00:00',
                        answer='2017-03-23T00:01:00+00:00',
                        end='2017-03-23T00:02:27+00:00',
                        destination_extension='3378',
                        destination_name=u'dést.',
                        duration=87,
                        direction='internal',
                        source_extension='7687',
                        source_name=u'soùr.'),
            has_entries(answered=False,
                        start='2017-03-23T11:11:11+00:00',
                        answer='2017-03-23T11:12:11+00:00',
                        end='2017-03-23T11:13:29+00:00',
                        destination_extension='8733',
                        destination_name=u'.tsèd',
                        duration=78,
                        direction='outbound',
                        source_extension='7867',
                        source_name=u'.rùos'),
        ),
                                        filtered=2,
                                        total=2))

    def test_given_wrong_params_when_list_cdr_then_400(self):
        wrong_params = {'abcd', '12:345', '2017-042-10'}
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(from_=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('from'))))
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(until=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('until'))))
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(direction=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('direction'))))
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(order=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('order'))))
        for wrong_param in wrong_params | {'-1'}:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(limit=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('limit'))))
        for wrong_param in wrong_params | {'-1'}:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(offset=wrong_param),
                raises(CallLogdError).matching(has_properties(status_code=400,
                                                              details=has_key('offset'))))

    def test_given_unsupported_params_when_list_cdr_then_400(self):
        assert_that(
            calling(self.call_logd.cdr.list).with_args(order='end'),
            raises(CallLogdError).matching(has_properties(status_code=400,
                                                          details=has_key('order'))))

    def test_given_call_logs_when_no_answered_then_end_equal_start(self):
        call_logs = [
            {'date': '2017-03-23 00:00:00',
             'date_answer': None}
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(start='2017-03-23T00:00:00+00:00',
                        end='2017-03-23T00:00:00+00:00'),
        )))

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
            {'date': '2017-04-10', 'duration': timedelta(seconds=0)},
            {'date': '2017-04-12', 'duration': timedelta(seconds=2)},
            {'date': '2017-04-11', 'duration': timedelta(seconds=1)},
        ]

        with self.call_logs(call_logs):
            result_start_asc = self.call_logd.cdr.list(order='start', direction='asc')
            result_start_desc = self.call_logd.cdr.list(order='start', direction='desc')
            result_duration = self.call_logd.cdr.list(order='duration', direction='asc')

        assert_that(result_start_asc, has_entry('items', contains(
            has_entries(start='2017-04-10T00:00:00+00:00'),
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-12T00:00:00+00:00'),
        )))

        assert_that(result_start_desc, has_entry('items', contains(
            has_entries(start='2017-04-12T00:00:00+00:00'),
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-10T00:00:00+00:00'),
        )))

        assert_that(result_duration, has_entry('items', contains(
            has_entries(duration=0),
            has_entries(duration=1),
            has_entries(duration=2),
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

    def test_given_call_logs_when_list_cdr_with_search_then_list_matching_cdr(self):
        call_logs = [
            {'date': '2016-04-10'},
            {'date': '2017-04-10'},
            {'date': '2016-04-12', 'source_exten': 'prefix2017'},
            {'date': '2016-04-12', 'source_name': '2017suffix'},
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list(search='2017')

        assert_that(result, has_entries(filtered=2,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('source_extension', 'prefix2017'),
                                            has_entry('source_name', '2017suffix'),
                                        )))

    def test_given_no_token_when_list_cdr_of_user_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list_for_user).with_args(SOME_USER_UUID),
            raises(CallLogdError).matching(has_properties(status_code=401,
                                                          message=contains_string_ignoring_case('unauthorized')))
        )
        self.call_logd.set_token(VALID_TOKEN)

    def test_given_call_logs_when_list_cdr_of_user_then_list_cdr_of_user(self):
        USER_1_UUID = '3eb6eaac-b99f-4c40-8ea9-597e26c76dd1'
        USER_2_UUID = 'de5ffb31-eacd-4fd7-b7e0-dd4b8676e346'

        call_logs = [
            {'date': '2017-04-10'},
            {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-12', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-13', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-14', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-15', 'participants': [{'user_uuid': USER_2_UUID}]},
        ]

        with self.call_logs(call_logs):
            result = self.call_logd.cdr.list_for_user(USER_1_UUID, limit=2, offset=1, order='start', direction='desc')

        assert_that(result, has_entries(filtered=4,
                                        total=6,
                                        items=contains(
                                            has_entries(start='2017-04-13T00:00:00+00:00'),
                                            has_entries(start='2017-04-12T00:00:00+00:00'),
                                        )))

    def test_given_no_token_when_list_my_cdr_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list_from_user),
            raises(CallLogdError).matching(has_properties(status_code=401,
                                                          message=contains_string_ignoring_case('unauthorized')))
        )
        self.call_logd.set_token(VALID_TOKEN)

    def test_given_token_with_no_user_uuid_when_list_my_cdr_then_400(self):
        self.call_logd.set_token(NON_USER_TOKEN)
        assert_that(
            calling(self.call_logd.cdr.list_from_user),
            raises(CallLogdError).matching(has_properties(status_code=400,
                                                          message=contains_string_ignoring_case('user')))
        )
        self.call_logd.set_token(VALID_TOKEN)

    def test_when_user_list_cdr_with_arg_user_uuid_then_user_uuid_is_ignored(self):
        USER_1_UUID = '3eb6eaac-b99f-4c40-8ea9-597e26c76dd1'
        USER_2_UUID = 'de5ffb31-eacd-4fd7-b7e0-dd4b8676e346'
        SOME_TOKEN = 'my-token'

        call_logs = [
            {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
        ]
        self.auth.set_token(MockUserToken(SOME_TOKEN, user_uuid=USER_1_UUID))

        with self.call_logs(call_logs):
            self.call_logd.set_token(SOME_TOKEN)
            result = self.call_logd.cdr.list_from_user(user_uuid=USER_2_UUID)
            self.call_logd.set_token(VALID_TOKEN)

        assert_that(result, has_entries(filtered=1,
                                        total=1,
                                        items=contains(
                                            has_entries(start='2017-04-11T00:00:00+00:00'),
                                        )))

    def test_given_call_logs_when_list_my_cdr_then_list_my_cdr(self):
        USER_1_UUID = '3eb6eaac-b99f-4c40-8ea9-597e26c76dd1'
        USER_2_UUID = 'de5ffb31-eacd-4fd7-b7e0-dd4b8676e346'
        SOME_TOKEN = 'my-token'

        call_logs = [
            {'date': '2017-04-10'},
            {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-12', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-13', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-14', 'participants': [{'user_uuid': USER_1_UUID}]},
            {'date': '2017-04-15', 'participants': [{'user_uuid': USER_2_UUID}]},
        ]
        self.auth.set_token(MockUserToken(SOME_TOKEN, user_uuid=USER_1_UUID))

        with self.call_logs(call_logs):
            self.call_logd.set_token(SOME_TOKEN)
            result = self.call_logd.cdr.list_from_user(limit=2, offset=1, order='start', direction='desc')
            self.call_logd.set_token(VALID_TOKEN)

        assert_that(result, has_entries(filtered=4,
                                        total=6,
                                        items=contains_inanyorder(
                                            has_entries(start='2017-04-13T00:00:00+00:00'),
                                            has_entries(start='2017-04-12T00:00:00+00:00'),
                                        )))

    @contextmanager
    def call_logs(self, call_logs):
        with self.database.queries() as queries:
            for call_log in call_logs:
                participants = call_log.pop('participants', [])
                call_log['id'] = queries.insert_call_log(**call_log)
                call_log['participants'] = participants
                for participant in participants:
                    queries.insert_call_log_participant(call_log_id=call_log['id'],
                                                        **participant)

        try:
            yield
        finally:
            with self.database.queries() as queries:
                for call_log in call_logs:
                    queries.delete_call_log(call_log['id'])
