# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from functools import wraps
from hamcrest import assert_that
from hamcrest import calling
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import has_properties
from hamcrest import not_
from hamcrest import only_contains
from datetime import timedelta
from xivo_call_logs_client.exceptions import CallLogdError
from xivo_test_helpers.hamcrest.raises import raises

from .test_api.auth import MockUserToken
from .test_api.base import IntegrationTest
from .test_api.constants import NON_USER_TOKEN
from .test_api.constants import VALID_TOKEN
from .test_api.hamcrest.contains_string_ignoring_case import contains_string_ignoring_case

SOME_USER_UUID = '7a0c6fe6-219d-4977-80e4-1bfc7ab0b289'
USER_1_UUID = '11111111-1111-1111-1111-111111111111'
USER_2_UUID = '22222222-2222-2222-2222-222222222222'
USER_3_UUID = '33333333-3333-3333-3333-333333333333'


def call_logs(call_logs):
    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.database.queries() as queries:
                for call_log in call_logs:
                    participants = call_log.pop('participants', [])
                    call_log['id'] = queries.insert_call_log(**call_log)
                    call_log['participants'] = participants
                    for participant in participants:
                        queries.insert_call_log_participant(call_log_id=call_log['id'],
                                                            **participant)
            try:
                return func(self, *args, **kwargs)
            finally:
                with self.database.queries() as queries:
                    for call_log in call_logs:
                        queries.delete_call_log(call_log['id'])
        return wrapped_function
    return _decorate


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

    @call_logs([
        {'id': 12,
         'answered': True,
         'date': '2017-03-23 00:00:00',
         'date_answer': '2017-03-23 00:01:00',
         'date_end': '2017-03-23 00:02:27',
         'destination_exten': '3378',
         'destination_name': u'dést.',
         'direction': 'internal',
         'source_exten': '7687',
         'source_name': u'soùr.',
         'participants': [{'user_uuid': '1',
                           'line_id': '1',
                           'tags': ['rh', 'Poudlard']}]},
        {'id': 34,
         'answered': False,
         'date': '2017-03-23 11:11:11',
         'date_answer': '2017-03-23 11:12:11',
         'date_end': '2017-03-23 11:13:29',
         'destination_exten': '8733',
         'destination_name': u'.tsèd',
         'duration': timedelta(seconds=78),
         'direction': 'outbound',
         'source_exten': '7867',
         'source_name': u'.rùos'},
    ])
    def test_given_call_logs_when_list_cdr_then_list_cdr(self):
        result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(id=12,
                        answered=True,
                        start='2017-03-23T00:00:00+00:00',
                        answer='2017-03-23T00:01:00+00:00',
                        end='2017-03-23T00:02:27+00:00',
                        destination_extension='3378',
                        destination_name=u'dést.',
                        duration=87,
                        call_direction='internal',
                        source_extension='7687',
                        source_name=u'soùr.',
                        tags=['rh', 'Poudlard']),
            has_entries(id=34,
                        answered=False,
                        start='2017-03-23T11:11:11+00:00',
                        answer='2017-03-23T11:12:11+00:00',
                        end='2017-03-23T11:13:29+00:00',
                        destination_extension='8733',
                        destination_name=u'.tsèd',
                        duration=78,
                        call_direction='outbound',
                        source_extension='7867',
                        source_name=u'.rùos',
                        tags=[]),
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

        assert_that(
            calling(self.call_logd.cdr.list).with_args(order='tags'),
            raises(CallLogdError).matching(has_properties(status_code=400,
                                                          details=has_key('order'))))

        assert_that(
            calling(self.call_logd.cdr.list).with_args(call_direction='not_valid_choice'),
            raises(CallLogdError).matching(has_properties(status_code=400,
                                                          details=has_key('call_direction'))))

    @call_logs([
        {'date': '2017-04-10'},
        {'date': '2017-04-11'},
        {'date': '2017-04-12'},
        {'date': '2017-04-13'},
    ])
    def test_given_call_logs_when_list_cdr_in_range_then_list_cdr_in_range(self):
        result = self.call_logd.cdr.list(from_='2017-04-11', until='2017-04-13')

        assert_that(result, has_entries(items=contains_inanyorder(
            has_entries(start='2017-04-11T00:00:00+00:00'),
            has_entries(start='2017-04-12T00:00:00+00:00'),
        ),
                                        filtered=2,
                                        total=4))

    @call_logs([
        {'date': '2017-04-10', 'date_answer': '2017-04-10', 'date_end': '2017-04-10'},
        {'date': '2017-04-12', 'date_answer': '2017-04-12', 'date_end': '2017-04-12 00:00:02'},
        {'date': '2017-04-11', 'date_answer': '2017-04-11', 'date_end': '2017-04-11 00:00:01'},
    ])
    def test_given_call_logs_when_list_cdr_in_order_then_list_cdr_in_order(self):
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

    @call_logs([
        {'date': '2017-04-10'},
        {'date': '2017-04-12'},
        {'date': '2017-04-11'},
    ])
    def test_given_call_logs_when_list_cdr_with_pagination_then_list_cdr_paginated(self):
        result_unpaginated = self.call_logd.cdr.list()
        result_paginated = self.call_logd.cdr.list(limit=1, offset=1)

        assert_that(result_paginated, has_entries(filtered=3,
                                                  total=3,
                                                  items=contains(
                                                      result_unpaginated['items'][1],
                                                  )))

    @call_logs([
        {'date': '2016-04-10'},
        {'date': '2017-04-10'},
        {'date': '2016-04-12', 'source_exten': 'prefix2017'},
        {'date': '2016-04-12', 'source_name': '2017suffix'},
    ])
    def test_given_call_logs_when_list_cdr_with_search_then_list_matching_cdr(self):
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

    @call_logs([
        {'date': '2016-04-10', 'direction': 'outbound'},
        {'date': '2017-04-10', 'direction': 'internal'},
        {'date': '2016-04-12'},
        {'date': '2016-04-12', 'direction': 'inbound'},
    ])
    def test_given_call_logs_when_list_cdr_with_call_direction_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(call_direction='internal')
        assert_that(result, has_entries(filtered=1,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('call_direction', 'internal'),
                                        )))

    @call_logs([
        {'date': '2016-04-10', 'source_exten': '12345'},
        {'date': '2017-04-10', 'source_exten': '123'},
        {'date': '2016-04-12'},
        {'date': '2016-04-12', 'destination_exten': '45'},
    ])
    def test_given_call_logs_when_list_cdr_with_number_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(number='_45')
        assert_that(result, has_entries(filtered=2,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('source_extension', '12345'),
                                            has_entry('destination_extension', '45'),
                                        )))

        result = self.call_logd.cdr.list(number='45')
        assert_that(result, has_entries(filtered=1,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('destination_extension', '45'),
                                        )))

        result = self.call_logd.cdr.list(number='_23_')
        assert_that(result, has_entries(filtered=2,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('source_extension', '12345'),
                                            has_entry('source_extension', '123'),
                                        )))

        result = self.call_logd.cdr.list(number='4_')
        assert_that(result, has_entries(filtered=1,
                                        total=4,
                                        items=contains_inanyorder(
                                            has_entry('destination_extension', '45'),
                                        )))

        result = self.call_logd.cdr.list(number='0123456789')
        assert_that(result, has_entries(filtered=0, total=4, items=empty()))

    @call_logs([
        {'date': '2017-04-11', 'participants': [{'user_uuid': '1', 'tags': ['quebec']}]},
        {'date': '2017-04-12'},
        {'date': '2017-04-13', 'participants': [{'user_uuid': '1', 'tags': ['quebec', 'montreal']}]},
        {'date': '2017-04-14', 'participants': [{'user_uuid': '1', 'tags': ['chicoutimi']},
                                                {'user_uuid': '1', 'tags': ['roberval']}]},
        {'date': '2017-04-15', 'participants': [{'user_uuid': '1', 'tags': ['alma', 'roberval', 'jonquiere']}]},
    ])
    def test_given_call_logs_when_list_cdr_with_tags_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(tags='chicoutimi')
        assert_that(result, has_entries(filtered=1,
                                        total=5,
                                        items=contains_inanyorder(
                                            has_entry('tags', contains_inanyorder('chicoutimi', 'roberval')),
                                        )))

        result = self.call_logd.cdr.list(tags='quebec')
        assert_that(result, has_entries(filtered=2,
                                        total=5,
                                        items=contains_inanyorder(
                                            has_entry('tags', contains_inanyorder('quebec')),
                                            has_entry('tags', contains_inanyorder('quebec', 'montreal')),
                                        )))

        result = self.call_logd.cdr.list(tags='chicoutimi,alma')
        assert_that(result, has_entries(filtered=0, total=5, items=empty()))

        result = self.call_logd.cdr.list(tags='roberval')
        assert_that(result, has_entries(filtered=2,
                                        total=5,
                                        items=contains_inanyorder(
                                            has_entry('tags', contains_inanyorder('chicoutimi', 'roberval')),
                                            has_entry('tags', contains_inanyorder('alma', 'roberval', 'jonquiere')),
                                        )))

        result = self.call_logd.cdr.list(tags='Mashteuiatsh')
        assert_that(result, has_entries(filtered=0, total=5, items=empty()))

    @call_logs([
        {'date': '2017-04-10'},
        {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-12', 'participants': [{'user_uuid': USER_1_UUID}, {'user_uuid': USER_3_UUID}]},
        {'date': '2017-04-13', 'participants': [{'user_uuid': USER_2_UUID}]},
        {'date': '2017-04-14', 'participants': [{'user_uuid': USER_3_UUID}]},
        {'date': '2017-04-15', 'participants': [{'user_uuid': USER_2_UUID}]},
    ])
    def test_given_call_logs_when_list_cdr_with_user_uuid_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(user_uuid=USER_3_UUID)
        assert_that(result, has_entries(filtered=2,
                                        total=6,
                                        items=contains_inanyorder(
                                            has_entries(start='2017-04-12T00:00:00+00:00'),
                                            has_entries(start='2017-04-14T00:00:00+00:00'),
                                        )))

        result = self.call_logd.cdr.list(user_uuid='{},{}'.format(USER_2_UUID, USER_3_UUID))
        assert_that(result, has_entries(filtered=4,
                                        total=6,
                                        items=contains_inanyorder(
                                            has_entries(start='2017-04-12T00:00:00+00:00'),
                                            has_entries(start='2017-04-13T00:00:00+00:00'),
                                            has_entries(start='2017-04-14T00:00:00+00:00'),
                                            has_entries(start='2017-04-15T00:00:00+00:00'),
                                        )))

    @call_logs([
        {'date': '2017-04-10'},
        {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-12', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-13', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-14', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-15', 'participants': [{'user_uuid': USER_2_UUID}]},
    ])
    def test_given_call_logs_when_list_cdr_of_user_then_list_cdr_of_user(self):
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

    @call_logs([
        {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
    ])
    def test_when_user_list_cdr_with_arg_user_uuid_then_user_uuid_is_ignored(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(MockUserToken(SOME_TOKEN, user_uuid=USER_1_UUID))

        self.call_logd.set_token(SOME_TOKEN)
        result = self.call_logd.cdr.list_from_user(user_uuid=USER_2_UUID)
        self.call_logd.set_token(VALID_TOKEN)

        assert_that(result, has_entries(filtered=1,
                                        total=1,
                                        items=contains(
                                            has_entries(start='2017-04-11T00:00:00+00:00'),
                                        )))
        assert_that(result, has_entries(items=only_contains(not_(has_key('tags')))))

    @call_logs([
        {'date': '2017-04-10'},
        {'date': '2017-04-11', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-12', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-13', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-14', 'participants': [{'user_uuid': USER_1_UUID}]},
        {'date': '2017-04-15', 'participants': [{'user_uuid': USER_2_UUID}]},
    ])
    def test_given_call_logs_when_list_my_cdr_then_list_my_cdr(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(MockUserToken(SOME_TOKEN, user_uuid=USER_1_UUID))

        self.call_logd.set_token(SOME_TOKEN)
        result = self.call_logd.cdr.list_from_user(limit=2, offset=1, order='start', direction='desc')
        self.call_logd.set_token(VALID_TOKEN)

        assert_that(result, has_entries(filtered=4,
                                        total=6,
                                        items=contains_inanyorder(
                                            has_entries(start='2017-04-13T00:00:00+00:00'),
                                            has_entries(start='2017-04-12T00:00:00+00:00'),
                                        )))
