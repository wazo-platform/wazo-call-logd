# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import requests

from io import StringIO
from hamcrest import (
    all_of,
    any_of,
    assert_that,
    calling,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    empty,
    has_entry,
    has_entries,
    has_items,
    has_key,
    has_length,
    has_properties,
    starts_with,
)
from wazo_call_logd_client.exceptions import CallLogdError
from xivo_test_helpers.auth import MockUserToken
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers.base import cdr, IntegrationTest
from .helpers.constants import (
    ALICE,
    BOB,
    CHARLES,
    NON_USER_TOKEN,
    OTHER_USER_UUID,
    OTHER_USER_TOKEN,
    OTHER_TENANT,
    USER_1_UUID,
    USER_2_UUID,
    USER_3_UUID,
    USERS_TENANT,
    USER_1_TOKEN,
    USER_2_TOKEN,
    MASTER_TOKEN,
    MASTER_TENANT,
    MINUTES,
    NOW,
)
from .helpers.database import call_log, call_logs
from .helpers.hamcrest.contains_string_ignoring_case import (
    contains_string_ignoring_case,
)


class TestNoAuth(IntegrationTest):
    def test_given_no_auth_when_list_cdr_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.cdr.list),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_list_cdr_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )

    def test_given_no_auth_when_get_cdr_by_id_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.cdr.get_by_id).with_args(cdr_id=33),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_get_cdr_by_id_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.get_by_id).with_args(cdr_id=33),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )


class TestGetCDRId(IntegrationTest):
    def test_given_wrong_id_when_get_cdr_by_id_then_404(self):
        assert_that(
            calling(self.call_logd.cdr.get_by_id).with_args(cdr_id=33),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=404,
                    message=contains_string_ignoring_case('no cdr found'),
                    details=has_key('cdr_id'),
                )
            ),
        )

    @call_log(
        **{'id': 12},
        date='2017-03-23 00:00:00',
        date_answer='2017-03-23 00:01:00',
        date_end='2017-03-23 00:02:27',
        destination_exten='3378',
        destination_name='dést,ination',
        destination_internal_exten='3245',
        destination_internal_context='internal',
        direction='internal',
        requested_name='réques,ted',
        requested_exten='3958',
        requested_internal_exten='3490',
        requested_internal_context='internal',
        source_exten='7687',
        source_name='soùr.',
        source_internal_exten='5938',
        source_internal_context='internal',
        participants=[
            {
                'user_uuid': USER_1_UUID,
                'line_id': '11',
                'tags': ['rh', 'Poudlard'],
                'role': 'source',
            },
            {'user_uuid': USER_2_UUID, 'line_id': '22', 'role': 'destination'},
        ],
        recordings=[
            {
                'start_time': '2017-03-23 00:01:01',
                'end_time': '2017-03-23 00:01:26',
                'path': '/tmp/foobar.wav',
            },
            {
                'start_time': '2017-03-23 00:01:27',
                'end_time': '2017-03-23 00:02:26',
                'path': None,
            },
        ],
    )
    def test_given_id_when_get_cdr_by_id_then_get_cdr_by_id(self):
        result = self.call_logd.cdr.get_by_id(12)
        recording_uuid_1 = result['recordings'][0]['uuid']
        recording_uuid_2 = result['recordings'][1]['uuid']
        assert_that(
            result,
            has_entries(
                id=12,
                tenant_uuid=MASTER_TENANT,
                answered=True,
                start='2017-03-23T00:00:00+00:00',
                answer='2017-03-23T00:01:00+00:00',
                end='2017-03-23T00:02:27+00:00',
                destination_extension='3378',
                destination_name='dést,ination',
                destination_user_uuid=USER_2_UUID,
                destination_line_id=22,
                destination_internal_extension='3245',
                destination_internal_context='internal',
                duration=87,
                call_direction='internal',
                requested_name='réques,ted',
                requested_extension='3958',
                requested_internal_extension='3490',
                requested_internal_context='internal',
                source_extension='7687',
                source_name='soùr.',
                source_internal_extension='5938',
                source_internal_context='internal',
                source_user_uuid=USER_1_UUID,
                source_line_id=11,
                tags=contains_inanyorder('rh', 'Poudlard'),
                recordings=contains_inanyorder(
                    has_entries(
                        uuid=uuid_(),
                        start_time='2017-03-23T00:01:01+00:00',
                        end_time='2017-03-23T00:01:26+00:00',
                        deleted=False,
                        filename=f'2017-03-23T00_01_01UTC-12-{recording_uuid_1}.wav',
                    ),
                    has_entries(
                        uuid=uuid_(),
                        start_time='2017-03-23T00:01:27+00:00',
                        end_time='2017-03-23T00:02:26+00:00',
                        deleted=True,
                        filename=f'2017-03-23T00_01_27UTC-12-{recording_uuid_2}.wav',
                    ),
                ),
            ),
        )

    @call_log(
        **{'id': 12},
        date='2017-03-23 00:00:00',
        date_answer='2017-03-23 00:01:00',
        date_end='2017-03-23 00:02:27',
        destination_exten='3378',
        destination_name='dést,ination',
        destination_internal_exten='3245',
        destination_internal_context='internal',
        direction='internal',
        requested_name='réques,ted',
        requested_exten='3958',
        requested_internal_exten='3490',
        requested_internal_context='internal',
        source_exten='7687',
        source_name='soùr.',
        source_internal_exten='5938',
        source_internal_context='internal',
        participants=[
            {
                'user_uuid': USER_1_UUID,
                'line_id': '1',
                'tags': ['rh', 'Poudlard'],
                'role': 'source',
            }
        ],
        recordings=[
            {
                'start_time': '2017-03-23 00:01:01',
                'end_time': '2017-03-23 00:01:26',
                'path': '/tmp/foobar.wav',
            },
            {
                'start_time': '2017-03-23 00:01:27',
                'end_time': '2017-03-23 00:02:26',
                'path': None,
            },
        ],
    )
    def test_given_id_when_get_cdr_by_id_csv_then_get_cdr_by_id_csv(self):
        result_raw = self.call_logd.cdr.get_by_id_csv(12)
        result = list(csv.DictReader(StringIO(result_raw)))[0]
        recording_uuid_1 = result['recording_1_uuid']
        recording_uuid_2 = result['recording_2_uuid']
        assert_that(
            result,
            has_entries(
                id='12',
                tenant_uuid=MASTER_TENANT,
                answered='True',
                start='2017-03-23T00:00:00+00:00',
                answer='2017-03-23T00:01:00+00:00',
                end='2017-03-23T00:02:27+00:00',
                destination_extension='3378',
                destination_name='dést,ination',
                destination_internal_extension='3245',
                destination_internal_context='internal',
                duration='87',
                requested_name='réques,ted',
                requested_extension='3958',
                requested_internal_extension='3490',
                requested_internal_context='internal',
                call_direction='internal',
                source_extension='7687',
                source_name='soùr.',
                source_internal_extension='5938',
                source_internal_context='internal',
                source_user_uuid=USER_1_UUID,
                tags=any_of('rh;Poudlard', 'Poudlard;rh'),
                recording_1_uuid=uuid_(),
                recording_1_start_time='2017-03-23T00:01:01+00:00',
                recording_1_end_time='2017-03-23T00:01:26+00:00',
                recording_1_deleted='False',
                recording_1_filename=f'2017-03-23T00_01_01UTC-12-{recording_uuid_1}.wav',
                recording_2_uuid=uuid_(),
                recording_2_start_time='2017-03-23T00:01:27+00:00',
                recording_2_end_time='2017-03-23T00:02:26+00:00',
                recording_2_deleted='True',
                recording_2_filename=f'2017-03-23T00_01_27UTC-12-{recording_uuid_2}.wav',
            ),
        )

    @call_log(
        **{'id': 10},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_1_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_2_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 12},
        tenant_uuid=OTHER_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': OTHER_USER_UUID, 'line_id': '1', 'role': 'source'}],
    )
    def test_get_cdr_by_id_multitenant(self):
        self.call_logd.set_token(USER_1_TOKEN)
        result = self.call_logd.cdr.get_by_id(10)
        assert_that(
            result, has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
        )

        result = self.call_logd.cdr.get_by_id(11)
        assert_that(
            result, has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
        )

        assert_that(
            calling(self.call_logd.cdr.get_by_id).with_args(cdr_id=12),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=404,
                    message=contains_string_ignoring_case('no cdr found'),
                    details=has_key('cdr_id'),
                )
            ),
        )

        self.call_logd.set_token(OTHER_USER_TOKEN)
        result = self.call_logd.cdr.get_by_id(12)
        assert_that(
            result,
            has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT),
        )

        self.call_logd.set_token(MASTER_TOKEN)
        result = self.call_logd.cdr.get_by_id(10)
        assert_that(
            result, has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
        )

        result = self.call_logd.cdr.get_by_id(11)
        assert_that(
            result, has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
        )

        result = self.call_logd.cdr.get_by_id(12)
        assert_that(
            result,
            has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT),
        )


class TestListCDR(IntegrationTest):
    def test_given_no_call_logs_when_list_cdr_then_empty_list(self):
        result = self.call_logd.cdr.list()

        assert_that(result, has_entries(items=empty(), filtered=0, total=0))

    @call_log(
        **{'id': 12},
        date='2017-03-23 00:00:00',
        date_answer='2017-03-23 00:01:00',
        date_end='2017-03-23 00:02:27',
        destination_exten='3378',
        destination_name='dést.',
        direction='internal',
        source_exten='7687',
        source_name='soùr.',
        participants=[
            {
                'user_uuid': USER_1_UUID,
                'line_id': '1',
                'tags': ['rh', 'Poudlard'],
                'role': 'source',
            }
        ],
        recordings=[
            {
                'start_time': '2017-03-23 00:01:01',
                'end_time': '2017-03-23 00:02:26',
                'path': '/tmp/foobar.wav',
            },
        ],
    )
    @call_log(
        **{'id': 34},
        date='2017-03-23 11:11:11',
        date_answer=None,
        date_end='2017-03-23 11:13:29',
        destination_exten='8733',
        destination_name='.tsèd',
        direction='outbound',
        source_exten='7867',
        source_name='.rùos',
    )
    def test_given_call_logs_when_list_cdr_then_list_cdr(self):
        result = self.call_logd.cdr.list()

        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(
                    has_entries(
                        id=12,
                        tenant_uuid=MASTER_TENANT,
                        answered=True,
                        start='2017-03-23T00:00:00+00:00',
                        answer='2017-03-23T00:01:00+00:00',
                        end='2017-03-23T00:02:27+00:00',
                        destination_extension='3378',
                        destination_name='dést.',
                        duration=87,
                        call_direction='internal',
                        source_extension='7687',
                        source_name='soùr.',
                        source_user_uuid=USER_1_UUID,
                        tags=contains_inanyorder('rh', 'Poudlard'),
                        recordings=contains_inanyorder(
                            has_entries(
                                uuid=uuid_(),
                                start_time='2017-03-23T00:01:01+00:00',
                                end_time='2017-03-23T00:02:26+00:00',
                                deleted=False,
                            )
                        ),
                    ),
                    has_entries(
                        id=34,
                        answered=False,
                        start='2017-03-23T11:11:11+00:00',
                        answer=None,
                        end='2017-03-23T11:13:29+00:00',
                        destination_extension='8733',
                        destination_name='.tsèd',
                        duration=None,
                        call_direction='outbound',
                        source_extension='7867',
                        source_name='.rùos',
                        tags=[],
                        recordings=[],
                    ),
                ),
                filtered=2,
                total=2,
            ),
        )

    @call_log(
        **{'id': 12},
        date='2017-03-23 00:00:00',
        date_answer='2017-03-23 00:01:00',
        date_end='2017-03-23 00:02:27',
        destination_exten='3378',
        destination_name='dést,ination',
        direction='internal',
        source_exten='7687',
        source_name='soùr.',
        participants=[
            {
                'user_uuid': USER_1_UUID,
                'line_id': '1',
                'tags': ['rh', 'Poudlard'],
                'role': 'source',
            }
        ],
        recordings=[
            {
                'start_time': '2017-03-23 00:01:01',
                'end_time': '2017-03-23 00:01:26',
                'path': '/tmp/foobar.wav',
            },
        ],
    )
    @call_log(
        **{'id': 34},
        date='2017-03-23 11:11:11',
        date_answer=None,
        date_end='2017-03-23 11:13:29',
        destination_exten='8733',
        destination_name='noitani,tsèd',
        direction='outbound',
        source_exten='7867',
        source_name='.rùos',
        recordings=[],
    )
    def test_given_call_logs_when_list_cdr_in_csv_then_list_cdr_in_csv(self):
        result_raw = self.call_logd.cdr.list_csv()
        result = list(csv.DictReader(StringIO(result_raw)))

        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    id='12',
                    tenant_uuid=MASTER_TENANT,
                    answered='True',
                    start='2017-03-23T00:00:00+00:00',
                    answer='2017-03-23T00:01:00+00:00',
                    end='2017-03-23T00:02:27+00:00',
                    destination_extension='3378',
                    destination_name='dést,ination',
                    duration='87',
                    call_direction='internal',
                    source_extension='7687',
                    source_name='soùr.',
                    source_user_uuid=USER_1_UUID,
                    tags=any_of('rh;Poudlard', 'Poudlard;rh'),
                    recording_1_uuid=uuid_(),
                    recording_1_start_time='2017-03-23T00:01:01+00:00',
                    recording_1_end_time='2017-03-23T00:01:26+00:00',
                    recording_1_deleted='False',
                ),
                has_entries(
                    id='34',
                    answered='False',
                    start='2017-03-23T11:11:11+00:00',
                    answer='',
                    end='2017-03-23T11:13:29+00:00',
                    destination_extension='8733',
                    destination_name='noitani,tsèd',
                    duration='',
                    call_direction='outbound',
                    source_extension='7867',
                    source_name='.rùos',
                    tags='',
                ),
            ),
            'CSV received: {}'.format(result_raw),
        )

    def test_given_wrong_params_when_list_cdr_then_400(self):
        wrong_params = {'abcd', '12:345', '2017-042-10'}
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(from_=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('from'))
                ),
            )
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(until=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('until'))
                ),
            )
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(direction=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('direction'))
                ),
            )
        for wrong_param in wrong_params:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(order=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('order'))
                ),
            )
        for wrong_param in wrong_params | {'-1'}:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(limit=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('limit'))
                ),
            )
        for wrong_param in wrong_params | {'-1'}:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(offset=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('offset'))
                ),
            )

        for wrong_param in wrong_params | {'-1'}:
            assert_that(
                calling(self.call_logd.cdr.list).with_args(recorded=wrong_param),
                raises(CallLogdError).matching(
                    has_properties(status_code=400, details=has_key('recorded'))
                ),
            )

    def test_given_error_when_list_cdr_as_csv_then_return_error_in_csv(self):
        assert_that(
            calling(self.call_logd.cdr.list_csv).with_args(from_='wrong'),
            raises(CallLogdError).matching(
                has_properties(status_code=400, details=has_key('from'))
            ),
        )

    def test_given_unsupported_params_when_list_cdr_then_400(self):
        for unsupported in ('end', 'tags', 'recordings'):
            assert_that(
                calling(self.call_logd.cdr.list).with_args(order=unsupported),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=400,
                        details=has_entries(
                            order=has_items(has_entries(constraint_id='enum'))
                        ),
                    ),
                ),
            )

        assert_that(
            calling(self.call_logd.cdr.list).with_args(
                call_direction='not_valid_choice'
            ),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=400,
                    details=has_entries(
                        call_direction=has_items(has_entries(constraint_id='enum'))
                    ),
                ),
            ),
        )

    @call_log(date='2017-04-10')
    @call_log(date='2017-04-11')
    @call_log(date='2017-04-12')
    @call_log(date='2017-04-13')
    def test_given_call_logs_when_list_cdr_in_range_then_list_cdr_in_range(self):
        result = self.call_logd.cdr.list(
            from_='2017-04-11T00:00:00', until='2017-04-13T00:00:00'
        )

        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(
                    has_entries(start='2017-04-11T00:00:00+00:00'),
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                ),
                filtered=2,
                total=4,
            ),
        )

    @call_log(date='2017-04-10', date_answer='2017-04-10', date_end='2017-04-10')
    @call_log(
        date='2017-04-12', date_answer='2017-04-12', date_end='2017-04-12 00:00:02'
    )
    @call_log(
        date='2017-04-11', date_answer='2017-04-11', date_end='2017-04-11 00:00:01'
    )
    def test_given_call_logs_when_list_cdr_in_order_then_list_cdr_in_order(self):
        result_start_asc = self.call_logd.cdr.list(order='start', direction='asc')
        result_start_desc = self.call_logd.cdr.list(order='start', direction='desc')
        result_duration = self.call_logd.cdr.list(order='duration', direction='asc')

        assert_that(
            result_start_asc,
            has_entry(
                'items',
                contains_exactly(
                    has_entries(start='2017-04-10T00:00:00+00:00'),
                    has_entries(start='2017-04-11T00:00:00+00:00'),
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                ),
            ),
        )

        assert_that(
            result_start_desc,
            has_entry(
                'items',
                contains_exactly(
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                    has_entries(start='2017-04-11T00:00:00+00:00'),
                    has_entries(start='2017-04-10T00:00:00+00:00'),
                ),
            ),
        )

        assert_that(
            result_duration,
            has_entry(
                'items',
                contains_exactly(
                    has_entries(duration=0),
                    has_entries(duration=1),
                    has_entries(duration=2),
                ),
            ),
        )

    @call_log(date='2017-04-10', date_answer=None, date_end='2017-04-10')
    @call_log(
        date='2017-04-12', date_answer='2017-04-12', date_end='2017-04-12 00:00:02'
    )
    @call_log(
        date='2017-04-11', date_answer='2017-04-11', date_end='2017-04-11 00:00:01'
    )
    def test_list_cdr_sort_nulls_last(self):
        duration_desc = self.call_logd.cdr.list(order='duration', direction='desc')
        duration_asc = self.call_logd.cdr.list(order='duration', direction='asc')

        assert_that(
            duration_asc['items'],
            contains_exactly(
                has_entries(duration=None),
                has_entries(duration=1),
                has_entries(duration=2),
            ),
        )
        assert_that(
            duration_desc['items'],
            contains_exactly(
                has_entries(duration=2),
                has_entries(duration=1),
                has_entries(duration=None),
            ),
        )

    @call_log(date='2017-04-10')
    @call_log(date='2017-04-12')
    @call_log(date='2017-04-11')
    def test_given_call_logs_when_list_cdr_with_pagination_then_list_cdr_paginated(
        self,
    ):
        result_unpaginated = self.call_logd.cdr.list()
        result_paginated = self.call_logd.cdr.list(limit=1, offset=1)

        assert_that(
            result_paginated,
            has_entries(
                filtered=3,
                total=3,
                items=contains_exactly(result_unpaginated['items'][1]),
            ),
        )

    @call_log(date='2016-04-10')
    @call_log(date='2017-04-10')
    @call_log(date='2016-04-12', source_exten='prefix2017')
    @call_log(date='2016-04-12', source_name='2017suffix')
    def test_given_call_logs_when_list_cdr_with_search_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(search='2017')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=4,
                items=contains_inanyorder(
                    has_entry('source_extension', 'prefix2017'),
                    has_entry('source_name', '2017suffix'),
                ),
            ),
        )

    @call_log(
        date='2017-03-23',
        recordings=[
            {
                'start_time': '2017-03-23 00:01:01',
                'end_time': '2017-03-23 00:01:26',
                'path': '/tmp/one.wav',
            }
        ],
    )
    @call_log(
        date='2017-03-23',
        recordings=[
            {
                'start_time': '2017-03-23 00:02:01',
                'end_time': '2017-03-23 00:02:26',
                'path': '/tmp/two.wav',
            }
        ],
    )
    def test_search_by_filename(self):
        expected = self.call_logd.cdr.list()['items'][0]
        result = self.call_logd.cdr.list(search=expected['recordings'][0]['filename'])
        assert_that(result, has_entries(items=contains_exactly(expected)))

    @call_logs(number=1100)
    def test_list_default_limit(self):
        result = self.call_logd.cdr.list()

        assert_that(
            result,
            all_of(has_entry('total', 1100), has_entry('items', has_length(1000))),
        )

    def test_given_no_token_when_list_cdr_of_user_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list_for_user).with_args(OTHER_USER_UUID),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )

    @call_log(date='2016-04-10', direction='outbound')
    @call_log(date='2017-04-10', direction='internal')
    @call_log(date='2016-04-12')
    @call_log(date='2016-04-12', direction='inbound')
    def test_given_call_logs_when_list_cdr_with_call_direction_then_list_matching_cdr(
        self,
    ):
        result = self.call_logd.cdr.list(call_direction='internal')
        assert_that(
            result,
            has_entries(
                filtered=1,
                total=4,
                items=contains_inanyorder(has_entry('call_direction', 'internal')),
            ),
        )

    @call_log(**cdr(id_=1, caller=ALICE, callee=BOB, start_time=NOW))
    @call_log(**cdr(id_=2, caller=ALICE, callee=BOB, start_time=NOW + 1 * MINUTES))
    @call_log(**cdr(id_=3, caller=BOB, callee=ALICE, start_time=NOW + 2 * MINUTES))
    @call_log(**cdr(id_=4, caller=ALICE, callee=CHARLES, start_time=NOW - 5 * MINUTES))
    def test_distinct_peer_exten(self):
        result = self.call_logd.cdr.list(distinct='peer_exten')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=4,
                items=contains_inanyorder(has_entries(id=3), has_entries(id=4)),
            ),
        )

    @call_log(date='2016-04-10', source_exten='12345')
    @call_log(date='2017-04-10', source_exten='123')
    @call_log(date='2016-04-12')
    @call_log(date='2016-04-12', destination_exten='45')
    def test_given_call_logs_when_list_cdr_with_number_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(number='_45')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=4,
                items=contains_inanyorder(
                    has_entry('source_extension', '12345'),
                    has_entry('destination_extension', '45'),
                ),
            ),
        )

        result = self.call_logd.cdr.list(number='45')
        assert_that(
            result,
            has_entries(
                filtered=1,
                total=4,
                items=contains_inanyorder(has_entry('destination_extension', '45')),
            ),
        )

        result = self.call_logd.cdr.list(number='_23_')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=4,
                items=contains_inanyorder(
                    has_entry('source_extension', '12345'),
                    has_entry('source_extension', '123'),
                ),
            ),
        )

        result = self.call_logd.cdr.list(number='4_')
        assert_that(
            result,
            has_entries(
                filtered=1,
                total=4,
                items=contains_inanyorder(has_entry('destination_extension', '45')),
            ),
        )

        result = self.call_logd.cdr.list(number='0123456789')
        assert_that(result, has_entries(filtered=0, total=4, items=empty()))

    @call_log(
        date='2017-04-11',
        participants=[{'user_uuid': USER_1_UUID, 'tags': ['quebec']}],
    )
    @call_log(date='2017-04-12')
    @call_log(
        date='2017-04-13',
        participants=[{'user_uuid': USER_1_UUID, 'tags': ['quebec', 'montreal']}],
    )
    @call_log(
        date='2017-04-14',
        participants=[
            {'user_uuid': USER_1_UUID, 'tags': ['chicoutimi']},
            {'user_uuid': USER_1_UUID, 'tags': ['roberval']},
        ],
    )
    @call_log(
        date='2017-04-15',
        participants=[
            {
                'user_uuid': USER_1_UUID,
                'tags': ['alma', 'roberval', 'jonquiere'],
            }
        ],
    )
    def test_given_call_logs_when_list_cdr_with_tags_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(tags='chicoutimi')
        assert_that(
            result,
            has_entries(
                filtered=1,
                total=5,
                items=contains_inanyorder(
                    has_entry('tags', contains_inanyorder('chicoutimi', 'roberval'))
                ),
            ),
        )

        result = self.call_logd.cdr.list(tags='quebec')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=5,
                items=contains_inanyorder(
                    has_entry('tags', contains_inanyorder('quebec')),
                    has_entry('tags', contains_inanyorder('quebec', 'montreal')),
                ),
            ),
        )

        result = self.call_logd.cdr.list(tags='chicoutimi,alma')
        assert_that(result, has_entries(filtered=0, total=5, items=empty()))

        result = self.call_logd.cdr.list(tags='roberval')
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=5,
                items=contains_inanyorder(
                    has_entry('tags', contains_inanyorder('chicoutimi', 'roberval')),
                    has_entry(
                        'tags', contains_inanyorder('alma', 'roberval', 'jonquiere')
                    ),
                ),
            ),
        )

        result = self.call_logd.cdr.list(tags='Mashteuiatsh')
        assert_that(result, has_entries(filtered=0, total=5, items=empty()))

    @call_log(date='2017-04-10')
    @call_log(date='2017-04-11', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(
        date='2017-04-12',
        participants=[
            {'user_uuid': USER_1_UUID},
            {'user_uuid': USER_3_UUID},
        ],
    )
    @call_log(date='2017-04-13', participants=[{'user_uuid': USER_2_UUID}])
    @call_log(date='2017-04-14', participants=[{'user_uuid': USER_3_UUID}])
    @call_log(date='2017-04-15', participants=[{'user_uuid': USER_2_UUID}])
    def test_given_call_logs_when_list_cdr_with_user_uuid_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(user_uuid=USER_3_UUID)
        assert_that(
            result,
            has_entries(
                filtered=2,
                total=6,
                items=contains_inanyorder(
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                    has_entries(start='2017-04-14T00:00:00+00:00'),
                ),
            ),
        )

        result = self.call_logd.cdr.list(
            user_uuid='{},{}'.format(USER_2_UUID, USER_3_UUID)
        )
        assert_that(
            result,
            has_entries(
                filtered=4,
                total=6,
                items=contains_inanyorder(
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                    has_entries(start='2017-04-13T00:00:00+00:00'),
                    has_entries(start='2017-04-14T00:00:00+00:00'),
                    has_entries(start='2017-04-15T00:00:00+00:00'),
                ),
            ),
        )

    @call_log(
        date='2019-06-13T12:00:00+00:00',
        participants=[
            {'user_uuid': USER_1_UUID, 'role': 'source'},
            {'user_uuid': USER_2_UUID, 'role': 'destination'},
        ],
    )
    @call_log(
        date='2019-06-13T13:00:00+00:00',
        participants=[
            {'user_uuid': USER_1_UUID, 'role': 'source'},
            {'user_uuid': USER_3_UUID, 'role': 'destination'},
        ],
    )
    @call_log(
        date='2019-06-13T14:00:00+00:00',
        participants=[
            {'user_uuid': USER_3_UUID, 'role': 'source'},
            {'user_uuid': USER_2_UUID, 'role': 'destination'},
        ],
    )
    def test_when_list_my_cdr_with_user_uuid_then_list_matching_cdr(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(
            MockUserToken(
                SOME_TOKEN,
                user_uuid=USER_1_UUID,
                metadata={"tenant_uuid": MASTER_TENANT},
            )
        )

        self.call_logd.set_token(SOME_TOKEN)

        results = self.call_logd.cdr.list_from_user(user_uuid=USER_3_UUID)

        assert_that(
            results,
            has_entries(
                filtered=1,
                total=2,
                items=contains_inanyorder(
                    has_entries(start='2019-06-13T13:00:00+00:00')
                ),
            ),
        )

        results = self.call_logd.cdr.list_from_user(
            user_uuid=','.join([USER_1_UUID, USER_2_UUID, USER_3_UUID])
        )

        assert_that(
            results,
            has_entries(
                filtered=2,
                total=2,
                items=contains_inanyorder(
                    has_entries(start='2019-06-13T12:00:00+00:00'),
                    has_entries(start='2019-06-13T13:00:00+00:00'),
                ),
            ),
        )

    @call_log(**{'id': 1000}, date='2017-04-10')
    @call_log(**{'id': 1001}, date='2017-04-11')
    @call_log(**{'id': 1002}, date='2017-04-12')
    def test_given_call_logs_when_list_cdr_with_from_id_then_list_matching_cdr(self):
        result = self.call_logd.cdr.list(from_id=1001)

        assert_that(
            result,
            has_entries(
                filtered=2,
                total=3,
                items=contains_inanyorder(
                    has_entries(start='2017-04-11T00:00:00+00:00'),
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                ),
            ),
        )

    @call_log(
        **{'id': 1},
        recordings=[{'path': '/tmp/foobar.wav'}],
    )
    @call_log(**{'id': 2})
    @call_log(
        **{'id': 3},
        recordings=[{'path': '/tmp/foobar2.wav'}],
    )
    def test_given_call_logs_when_list_cdr_recorded_filter_then_list_recorded(self):
        results = self.call_logd.cdr.list(recorded=True)
        assert_that(
            results,
            has_entries(
                filtered=2,
                total=3,
                items=contains_inanyorder(
                    has_entries(id=1),
                    has_entries(id=3),
                ),
            ),
        )
        results = self.call_logd.cdr.list(recorded=False)
        assert_that(
            results,
            has_entries(
                filtered=1,
                total=3,
                items=contains_inanyorder(
                    has_entries(id=2),
                ),
            ),
        )

    @call_log(date='2017-04-10', date_answer='2017-04-10', date_end='2017-04-09')
    def test_negative_duration_then_duration_is_zero(self):
        result = self.call_logd.cdr.list()

        assert_that(
            result, has_entry('items', contains_exactly(has_entries(duration=0)))
        )

    @call_log(date='2017-04-10')
    @call_log(date='2017-04-11', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-12', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-13', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-14', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-15', participants=[{'user_uuid': USER_2_UUID}])
    def test_given_call_logs_when_list_cdr_of_user_then_list_cdr_of_user(self):
        result = self.call_logd.cdr.list_for_user(
            USER_1_UUID, limit=2, offset=1, order='start', direction='desc'
        )

        assert_that(
            result,
            has_entries(
                filtered=4,
                total=6,
                items=contains_exactly(
                    has_entries(start='2017-04-13T00:00:00+00:00'),
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                ),
            ),
        )

    @call_log(
        **{'id': 1},
        recordings=[{'path': '/tmp/foobar.wav'}],
        participants=[{'user_uuid': USER_1_UUID}],
    )
    @call_log(
        **{'id': 2},
        participants=[{'user_uuid': USER_1_UUID}],
    )
    @call_log(
        **{'id': 3},
        recordings=[{'path': '/tmp/foobar2.wav'}],
        participants=[{'user_uuid': USER_2_UUID}],
    )
    def test_given_call_logs_when_list_cdr_of_user_recorded_filter_then_list_recorded(
        self,
    ):
        results = self.call_logd.cdr.list_for_user(USER_1_UUID, recorded=True)
        assert_that(
            results,
            has_entries(
                filtered=1,
                total=3,
                items=contains_inanyorder(
                    has_entries(id=1),
                ),
            ),
        )
        results = self.call_logd.cdr.list_for_user(USER_1_UUID, recorded=False)
        assert_that(
            results,
            has_entries(
                filtered=1,
                total=3,
                items=contains_inanyorder(
                    has_entries(id=2),
                ),
            ),
        )

    @call_log(date='2017-04-11', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-12', participants=[{'user_uuid': USER_1_UUID}])
    def test_given_call_logs_when_list_cdr_of_user_as_csv_then_list_cdr_of_user_as_csv(
        self,
    ):
        result_raw = self.call_logd.cdr.list_for_user_csv(USER_1_UUID)
        result = list(csv.DictReader(StringIO(result_raw)))

        assert_that(
            result,
            contains_inanyorder(
                has_entries(start='2017-04-11T00:00:00+00:00'),
                has_entries(start='2017-04-12T00:00:00+00:00'),
            ),
            'CSV received: {}'.format(result_raw),
        )

    def test_given_no_token_when_list_my_cdr_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.cdr.list_from_user),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )

    def test_given_token_with_no_user_uuid_when_list_my_cdr_then_400(self):
        self.call_logd.set_token(NON_USER_TOKEN)
        assert_that(
            calling(self.call_logd.cdr.list_from_user),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=400, message=contains_string_ignoring_case('user')
                )
            ),
        )

    @call_log(date='2017-04-10')
    @call_log(date='2017-04-11', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-12', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-13', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-14', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-15', participants=[{'user_uuid': USER_2_UUID}])
    def test_given_call_logs_when_list_my_cdr_then_list_my_cdr(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(
            MockUserToken(
                SOME_TOKEN,
                user_uuid=USER_1_UUID,
                metadata={"tenant_uuid": MASTER_TENANT},
            )
        )

        self.call_logd.set_token(SOME_TOKEN)
        result = self.call_logd.cdr.list_from_user(
            limit=2, offset=1, order='start', direction='desc'
        )

        assert_that(
            result,
            has_entries(
                filtered=4,
                total=4,
                items=contains_inanyorder(
                    has_entries(start='2017-04-13T00:00:00+00:00'),
                    has_entries(start='2017-04-12T00:00:00+00:00'),
                ),
            ),
        )

    @call_log(date='2017-04-11', participants=[{'user_uuid': USER_1_UUID}])
    @call_log(date='2017-04-12', participants=[{'user_uuid': USER_1_UUID}])
    def test_given_call_logs_when_list_my_cdr_as_csv_then_list_my_cdr_as_csv(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(
            MockUserToken(
                SOME_TOKEN,
                user_uuid=USER_1_UUID,
                metadata={"tenant_uuid": MASTER_TENANT},
            )
        )

        self.call_logd.set_token(SOME_TOKEN)
        result_raw = self.call_logd.cdr.list_from_user_csv()
        result = list(csv.DictReader(StringIO(result_raw)))

        assert_that(
            result,
            contains_inanyorder(
                has_entries(start='2017-04-11T00:00:00+00:00'),
                has_entries(start='2017-04-12T00:00:00+00:00'),
            ),
            'CSV received: {}'.format(result_raw),
        )

    @call_logs(number=1100, participant_user=USER_1_UUID)
    def test_list_my_cdr_default_limit(self):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(
            MockUserToken(
                SOME_TOKEN,
                user_uuid=USER_1_UUID,
                metadata={"tenant_uuid": MASTER_TENANT},
            )
        )

        self.call_logd.set_token(SOME_TOKEN)
        result = self.call_logd.cdr.list_from_user()

        assert_that(
            result,
            all_of(has_entry('total', 1100), has_entry('items', has_length(1000))),
        )

    @call_log(
        **{'id': 1},
        recordings=[{'path': '/tmp/foobar.wav'}],
        participants=[{'user_uuid': USER_1_UUID}],
    )
    @call_log(**{'id': 2}, participants=[{'user_uuid': USER_1_UUID}])
    @call_log(
        **{'id': 3},
        recordings=[{'path': '/tmp/foobar2.wav'}],
        participants=[{'user_uuid': USER_2_UUID}],
    )
    def test_given_call_logs_when_list_my_cdr_recorded_filter_then_list_my_recorded_cdr(
        self,
    ):
        SOME_TOKEN = 'my-token'
        self.auth.set_token(
            MockUserToken(
                SOME_TOKEN,
                user_uuid=USER_1_UUID,
                metadata={"tenant_uuid": MASTER_TENANT},
            )
        )

        self.call_logd.set_token(SOME_TOKEN)
        results = self.call_logd.cdr.list_from_user(recorded=True)
        assert_that(
            results,
            has_entries(
                filtered=1,
                total=2,
                items=contains_inanyorder(
                    has_entries(id=1),
                ),
            ),
        )
        results = self.call_logd.cdr.list_from_user(recorded=False)
        assert_that(
            results,
            has_entries(
                filtered=1,
                total=2,
                items=contains_inanyorder(
                    has_entries(id=2),
                ),
            ),
        )

    @call_log(
        **{'id': 10},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_1_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_2_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 12},
        tenant_uuid=OTHER_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': OTHER_USER_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(**{'id': 13}, date='2017-03-23 00:00:00', tenant_uuid=MASTER_TENANT)
    def test_list_multitenant(self):
        self.call_logd.set_token(USER_1_TOKEN)
        results = self.call_logd.cdr.list_from_user()
        assert_that(results['total'], equal_to(1))
        assert_that(
            results['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        results = self.call_logd.cdr.list_for_user(USER_2_UUID)
        assert_that(results['total'], equal_to(2))
        assert_that(results['filtered'], equal_to(1))
        assert_that(
            results['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        results = self.call_logd.cdr.list_for_user(OTHER_USER_UUID)
        assert_that(results['total'], equal_to(2))
        assert_that(results['filtered'], equal_to(0))

        self.call_logd.set_token(USER_2_TOKEN)
        results = self.call_logd.cdr.list_from_user()
        assert_that(results['total'], equal_to(1))
        assert_that(
            results['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        self.call_logd.set_token(OTHER_USER_TOKEN)
        results = self.call_logd.cdr.list_from_user()
        assert_that(results['total'], equal_to(1))
        assert_that(
            results['items'],
            contains_exactly(
                has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT)
            ),
        )

        self.call_logd.set_token(MASTER_TOKEN)
        results = self.call_logd.cdr.list()
        assert_that(results['total'], equal_to(1))
        assert_that(results['filtered'], equal_to(1))
        assert_that(
            results,
            has_entries(
                items=contains_inanyorder(has_entries(tenant_uuid=MASTER_TENANT))
            ),
        )

        self.call_logd.set_token(USER_1_TOKEN)
        results = self.call_logd.cdr.list()
        assert_that(results['total'], equal_to(2))
        assert_that(
            results,
            has_entries(
                items=contains_inanyorder(
                    has_entries(source_user_uuid=USER_1_UUID),
                    has_entries(source_user_uuid=USER_2_UUID),
                )
            ),
        )

        self.call_logd.set_token(MASTER_TOKEN)
        results = self.call_logd.cdr.list(recurse=True)
        assert_that(results['total'], equal_to(4))
        assert_that(
            results['items'],
            contains_inanyorder(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT),
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT),
                has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT),
                has_entries(tenant_uuid=MASTER_TENANT),
            ),
        )

    @call_log(
        **{'id': 10},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_1_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_2_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 12},
        tenant_uuid=OTHER_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': OTHER_USER_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(**{'id': 13}, date='2017-03-23 00:00:00', tenant_uuid=MASTER_TENANT)
    def test_list_multitenant_token_and_tenant_as_query_string(self):
        port = self.service_port(9298, 'call-logd')

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={'format': 'csv', 'token': USER_1_TOKEN},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/{USER_2_UUID}/cdr',
            params={
                'token': USER_1_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'csv',
            },
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/{OTHER_USER_UUID}/cdr',
            params={
                'token': USER_1_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'csv',
            },
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(result, empty())

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={
                'token': USER_2_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'csv',
            },
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={'token': OTHER_USER_TOKEN, 'format': 'csv'},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/cdr',
            params={'token': MASTER_TOKEN, 'format': 'csv'},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(has_entries(tenant_uuid=MASTER_TENANT)),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/cdr',
            params={'token': USER_1_TOKEN, 'format': 'csv'},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_inanyorder(
                has_entries(source_user_uuid=USER_1_UUID),
                has_entries(source_user_uuid=USER_2_UUID),
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/cdr',
            params={'token': MASTER_TOKEN, 'recurse': True, 'format': 'csv'},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_inanyorder(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT),
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT),
                has_entries(source_user_uuid=OTHER_USER_UUID, tenant_uuid=OTHER_TENANT),
                has_entries(tenant_uuid=MASTER_TENANT),
            ),
        )

    @call_log(
        **{'id': 10},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_1_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 11},
        tenant_uuid=USERS_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': USER_2_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(
        **{'id': 12},
        tenant_uuid=OTHER_TENANT,
        date='2017-03-23 00:00:00',
        participants=[{'user_uuid': OTHER_USER_UUID, 'line_id': '1', 'role': 'source'}],
    )
    @call_log(**{'id': 13}, date='2017-03-23 00:00:00', tenant_uuid=MASTER_TENANT)
    def test_list_format_parameter(self):
        port = self.service_port(9298, 'call-logd')

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={'format': 'csv', 'token': USER_1_TOKEN},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={'format': 'json', 'token': USER_1_TOKEN},
        )
        assert_that(
            response.json()['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_1_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/{USER_2_UUID}/cdr',
            params={
                'token': USER_1_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'csv',
            },
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/{USER_2_UUID}/cdr',
            params={
                'token': USER_1_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'json',
            },
        )
        assert_that(
            response.json()['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={
                'token': USER_2_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'csv',
            },
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={
                'token': USER_2_TOKEN,
                'tenant_uuids': USERS_TENANT,
                'format': 'json',
            },
        )
        assert_that(
            response.json()['items'],
            contains_exactly(
                has_entries(source_user_uuid=USER_2_UUID, tenant_uuid=USERS_TENANT)
            ),
        )

        response = requests.get(
            f'http://localhost:{port}/1.0/cdr',
            params={'token': MASTER_TOKEN, 'format': 'csv'},
        )
        result = list(csv.DictReader(StringIO(response.text)))
        assert_that(
            result,
            contains_exactly(has_entries(tenant_uuid=MASTER_TENANT)),
        )
        response = requests.get(
            f'http://localhost:{port}/1.0/cdr',
            params={'token': MASTER_TOKEN, 'format': 'json'},
        )
        assert_that(
            response.json()['items'],
            contains_exactly(has_entries(tenant_uuid=MASTER_TENANT)),
        )

    def test_list_csv_export_adds_the_content_disposition_header(self):
        port = self.service_port(9298, 'call-logd')

        response = requests.get(
            f'http://localhost:{port}/1.0/users/me/cdr',
            params={'format': 'csv', 'token': USER_1_TOKEN},
        )
        assert_that(
            response.headers,
            has_entries(
                'Content-Disposition', starts_with('attachment; filename=cdr-')
            ),
        )
