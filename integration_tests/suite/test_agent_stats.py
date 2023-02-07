# Copyright 2020-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytz

from datetime import timedelta

from hamcrest import (
    assert_that,
    calling,
    empty,
    equal_to,
    has_entries,
    has_items,
    has_properties,
)

from wazo_call_logd_client.exceptions import CallLogdError
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.constants import MASTER_TENANT
from .helpers.database import stat_agent_periodic, stat_agent, stat_call_on_queue
from .helpers.hamcrest.contains_string_ignoring_case import (
    contains_string_ignoring_case,
)

from .helpers.base import IntegrationTest


class TestNoAuth(IntegrationTest):
    def test_given_no_auth_when_list_agents_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.agent_statistics.list),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_list_agents_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.agent_statistics.list),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )

    def test_given_no_auth_when_get_agent_stats_by_id_then_503(self):
        with self.auth_stopped():
            assert_that(
                calling(self.call_logd.agent_statistics.get_by_id).with_args(
                    agent_id=33
                ),
                raises(CallLogdError).matching(
                    has_properties(
                        status_code=503, message=contains_string_ignoring_case('auth')
                    )
                ),
            )

    def test_given_no_token_when_get_agent_stats_by_id_then_401(self):
        self.call_logd.set_token(None)
        assert_that(
            calling(self.call_logd.agent_statistics.get_by_id).with_args(agent_id=33),
            raises(CallLogdError).matching(
                has_properties(
                    status_code=401,
                    message=contains_string_ignoring_case('unauthorized'),
                )
            ),
        )


class TestInputParameters(IntegrationTest):
    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:35:12', 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00'})
    # fmt: on
    def test_that_getting_agent_stats_with_wrong_parameters_returns_error(self):
        erronous_bodies = [
            # from_
            {'from_': 'test'},
            {'from_': False},
            {'from_': 1234},
            {'from_': '2020-10-05'},
            # until
            {'until': 'test'},
            {'until': False},
            {'until': 1234},
            {'until': '2020-10-05'},
            # interval
            {'interval': 'test'},
            {'interval': False},
            {'interval': 1234},
            # day_start_time
            {'day_start_time': 'test'},
            {'day_start_time': False},
            {'day_start_time': 1234},
            {'day_start_time': 124.5},
            {'day_start_time': '2020-10-06 10:00:00'},
            # day_end_time
            {'day_end_time': 'test'},
            {'day_end_time': False},
            {'day_end_time': 1234},
            {'day_end_time': 124.5},
            {'day_end_time': '2020-10-06 10:00:00'},
            # logic
            {'day_start_time': '25:00'},
            {'day_start_time': '23:60'},
            {'day_end_time': '25:00'},
            {'day_end_time': '23:60'},
            {'day_start_time': '23:00', 'day_end_time': '22:00'},
            {
                'from_': '2020-10-01 00:00:00',
                'until': '2020-11-01 00:00:01',
                'interval': 'hour',
            },
            {'week_days': 42},
            {'week_days': '6,7,8'},
            {'week_days': 'test'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-09T23:59:59'},
            {
                'from_': '2020-10-10T00:00:00+00:00',
                'until': '2020-10-10T00:00:00+01:00',
            },
            # Timezone
            {'timezone': 'invalid'},
            {'timezone': 1234},
        ]
        for body in erronous_bodies:
            assert_that(
                calling(self.call_logd.agent_statistics.get_by_id).with_args(
                    agent_id=42, **body
                ),
                raises(CallLogdError).matching(has_properties(status_code=400)),
                body,
            )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:35:12', 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00'})
    # fmt: on
    def test_that_listing_agents_stats_with_wrong_parameters_returns_error(self):
        erroneous_bodies = [
            # from_
            {'from_': 'test'},
            {'from_': False},
            {'from_': 1234},
            {'from_': '2020-10-05'},
            # until
            {'until': 'test'},
            {'until': False},
            {'until': 1234},
            {'until': '2020-10-05'},
            # day_start_time
            {'day_start_time': 'test'},
            {'day_start_time': False},
            {'day_start_time': 1234},
            {'day_start_time': 124.5},
            {'day_start_time': '2020-10-06 10:00:00'},
            # day_end_time
            {'day_end_time': 'test'},
            {'day_end_time': False},
            {'day_end_time': 1234},
            {'day_end_time': 124.5},
            {'day_end_time': '2020-10-06 10:00:00'},
            # logic
            {'day_start_time': '25:00'},
            {'day_start_time': '23:60'},
            {'day_end_time': '25:00'},
            {'day_end_time': '23:60'},
            {'day_start_time': '23:00', 'day_end_time': '22:00'},
            {'week_days': 42},
            {'week_days': '6,7,8'},
            {'week_days': 'test'},
            {'from_': '2020-10-10T00:00:00', 'until': '2020-10-09T23:59:59'},
            {
                'from_': '2020-10-10T00:00:00+00:00',
                'until': '2020-10-10T00:00:00+01:00',
            },
            # Timezone
            {'timezone': 'invalid'},
            {'timezone': 1234},
        ]
        for body in erroneous_bodies:
            assert_that(
                calling(self.call_logd.agent_statistics.list).with_args(**body),
                raises(CallLogdError).matching(has_properties(status_code=400)),
                body,
            )


class TestStatistics(IntegrationTest):
    def test_list_agent_statistics_when_no_stats(self):
        results = self.call_logd.agent_statistics.list()
        assert_that(
            results,
            has_entries(
                items=empty(),
                total=equal_to(0),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent({'id': 2, 'name': 'Agent/1002', 'agent_id': 10})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-05 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-05 13:25:31', 'talktime': 12, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-05 13:00:00', 'login_time': '00:55:00', 'pause_time': '00:15:00', 'wrapup_time': '00:02:00'})
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-06 13:59:00', 'talktime': 14, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:08:00', 'wrapup_time': '00:10:00'})
    # fmt: on
    def test_list_agent_statistics_when_no_param_with_stats(self):
        results = self.call_logd.agent_statistics.list()
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-05T13:00:00+00:00'},
                        until=self._get_tomorrow(),
                        tenant_uuid=MASTER_TENANT,
                        agent_id=42,
                        agent_number='1001',
                        conversation_time=timedelta(seconds=11 + 12).total_seconds(),
                        login_time=timedelta(minutes=55).total_seconds(),
                        pause_time=timedelta(minutes=15).total_seconds(),
                        wrapup_time=timedelta(minutes=2).total_seconds(),
                    ),
                    has_entries(
                        **{'from': '2020-10-06T13:00:00+00:00'},
                        until=self._get_tomorrow(),
                        tenant_uuid=MASTER_TENANT,
                        agent_id=10,
                        agent_number='1002',
                        conversation_time=timedelta(seconds=14).total_seconds(),
                        login_time=timedelta(hours=1).total_seconds(),
                        pause_time=timedelta(minutes=8).total_seconds(),
                        wrapup_time=timedelta(minutes=10).total_seconds(),
                    ),
                ),
                total=equal_to(2),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent({'id': 2, 'name': 'Agent/1002', 'agent_id': 10})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-05 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-05 13:25:31', 'talktime': 12, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-05 13:00:00', 'login_time': '00:55:00', 'pause_time': '00:15:00', 'wrapup_time': '00:02:00'})
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-06 13:59:00', 'talktime': 14, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:08:00', 'wrapup_time': '00:10:00'})
    # fmt: on
    def test_list_agent_statistics_when_no_param_except_timezone_with_stats(self):
        results = self.call_logd.agent_statistics.list(timezone='America/Montreal')
        timezone = pytz.timezone('America/Montreal')
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-05T09:00:00-04:00'},
                        until=self._get_tomorrow(timezone),
                        tenant_uuid=MASTER_TENANT,
                        agent_id=42,
                        agent_number='1001',
                        conversation_time=timedelta(seconds=11 + 12).total_seconds(),
                        login_time=timedelta(minutes=55).total_seconds(),
                        pause_time=timedelta(minutes=15).total_seconds(),
                        wrapup_time=timedelta(minutes=2).total_seconds(),
                    ),
                    has_entries(
                        **{'from': '2020-10-06T09:00:00-04:00'},
                        until=self._get_tomorrow(timezone),
                        tenant_uuid=MASTER_TENANT,
                        agent_id=10,
                        agent_number='1002',
                        conversation_time=timedelta(seconds=14).total_seconds(),
                        login_time=timedelta(hours=1).total_seconds(),
                        pause_time=timedelta(minutes=8).total_seconds(),
                        wrapup_time=timedelta(minutes=10).total_seconds(),
                    ),
                ),
                total=equal_to(2),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:08:00', 'wrapup_time': '00:10:00'})
    # fmt: on
    def test_list_agent_statistics_period_no_interval(self):
        results = self.call_logd.agent_statistics.list(
            from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00'
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **common_fields,
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        answered=1,
                        conversation_time=timedelta(seconds=11).total_seconds(),
                        login_time=timedelta(hours=1).total_seconds(),
                        pause_time=timedelta(minutes=8).total_seconds(),
                        wrapup_time=timedelta(minutes=10).total_seconds(),
                    )
                ),
                total=equal_to(1),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent({'id': 2, 'name': 'Agent/1010', 'agent_id': 100})
    @stat_agent({'id': 3, 'name': 'Agent/1002', 'agent_id': 1})
    @stat_agent({'id': 4, 'name': 'Agent/1003', 'agent_id': 2})
    @stat_agent({'id': 5, 'name': 'Agent/1066', 'agent_id': 10})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 4:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-06 7:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    @stat_agent_periodic({'agent_id': 3, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    @stat_agent_periodic({'agent_id': 4, 'time': '2020-11-01 00:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    # fmt: on
    def test_list_agent_statistics_multiple_agents_same_datetime(self):
        results = self.call_logd.agent_statistics.list(
            from_='2020-10-01 00:00:00', until='2020-11-01 00:00:00+00:00'
        )
        assert_that(
            results,
            has_entries(
                items=has_items(
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        agent_id=42,
                        agent_number='1001',
                        login_time=timedelta(hours=1).total_seconds(),
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        agent_id=100,
                        agent_number='1010',
                        login_time=timedelta(hours=1).total_seconds(),
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        agent_id=1,
                        agent_number='1002',
                        login_time=timedelta(hours=1).total_seconds(),
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        agent_id=2,
                        agent_number='1003',
                        login_time=0,
                    ),
                    has_entries(
                        **{'from': '2020-10-01T00:00:00+00:00'},
                        until='2020-11-01T00:00:00+00:00',
                        agent_id=10,
                        agent_number='1066',
                        login_time=0,
                    ),
                ),
                total=equal_to(5),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    #
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 7:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:15', 'wrapup_time': '00:00:00'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 7:05:24', 'talktime': 915, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 7:17:042', 'talktime': 547, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 7:54:16', 'talktime': 128, 'status': 'answered'})
    #
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00', 'login_time': '00:45:00', 'pause_time': '00:25:00', 'wrapup_time': '00:00:00'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:27:27', 'talktime': 654, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:32:44', 'talktime': 543, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 13:50:12', 'talktime': 321, 'status': 'answered'})
    #
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-10 16:00:00', 'login_time': '00:53:00', 'pause_time': '00:00:00', 'wrapup_time': '00:17:00'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 16:12:12', 'talktime': 60, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 16:23:23', 'talktime': 60, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-06 16:34:34', 'talktime': 60, 'status': 'answered'})
    # fmt: on
    def test_get_agent_no_params(self):
        results = self.call_logd.agent_statistics.get_by_id(agent_id=42)
        assert_that(results, has_entries(total=equal_to(1)))

        conversation_time = timedelta(
            seconds=915 + 547 + 128 + 654 + 543 + 321 + 60 + 60 + 60
        ).total_seconds()
        login_time = timedelta(hours=1, minutes=45 + 53).total_seconds()
        pause_time = timedelta(minutes=25, seconds=15).total_seconds()
        wrapup_time = timedelta(minutes=17).total_seconds()
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T07:00:00+00:00'},
                    until=self._get_tomorrow(),
                    tenant_uuid=MASTER_TENANT,
                    agent_id=42,
                    agent_number='1001',
                    answered=9,
                    conversation_time=conversation_time,
                    login_time=login_time,
                    pause_time=pause_time,
                    wrapup_time=wrapup_time,
                )
            ),
        )

    def test_get_agent_non_existing(self):
        assert_that(
            calling(self.call_logd.agent_statistics.get_by_id).with_args(agent_id=1),
            raises(CallLogdError).matching(has_properties(status_code=404)),
        )

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_get_agent_when_no_stats(self):
        results = self.call_logd.agent_statistics.get_by_id(agent_id=42)
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': None},
                    until=self._get_tomorrow(),
                    tenant_uuid=MASTER_TENANT,
                    agent_id=42,
                    agent_number='1001',
                    answered=0,
                    conversation_time=0,
                    login_time=0,
                    pause_time=0,
                    wrapup_time=0,
                )
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 7:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-10 16:00:00', 'login_time': '01:00:00'})
    # fmt: on
    def test_get_agent_no_interval_returns_from_to_until(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06T00:00:00+00:00',
            until='2020-10-07T00:00:00+00:00',
        )
        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    tenant_uuid=MASTER_TENANT,
                    agent_id=42,
                    agent_number='1001',
                    answered=0,
                    conversation_time=0,
                    login_time=timedelta(hours=2).total_seconds(),
                    pause_time=0,
                    wrapup_time=0,
                )
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 00:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 01:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 02:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 03:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 04:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 05:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 06:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 07:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 08:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 09:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 10:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 11:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 12:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 14:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 15:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 16:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 17:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 18:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 19:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 20:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 21:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 22:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 23:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 00:00:00', 'login_time': '01:00:00'})
    # fmt: on
    def test_get_agent_over_24_hours(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06T00:00:00+00:00',
            until='2020-10-07T23:59:59+00:00',
        )
        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T23:59:59+00:00',
                    tenant_uuid=MASTER_TENANT,
                    agent_id=42,
                    agent_number='1001',
                    login_time=timedelta(hours=25).total_seconds(),
                )
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 4:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 5:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 23:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 00:00:00', 'login_time': '01:00:00'})
    # fmt: on
    def test_get_agent_interval_by_hour(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='hour',
        )
        assert_that(results, has_entries(total=equal_to(25)))

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T04:00:00+00:00'},
                    until='2020-10-06T05:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T05:00:00+00:00'},
                    until='2020-10-06T06:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    login_time=timedelta(hours=1 + 1 + 1).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 7:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 13:00:00', 'login_time': '01:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 16:00:00', 'login_time': '01:00:00'})
    # fmt: on
    def test_get_agent_when_call_out_of_time_range(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='hour',
            day_start_time='08:00',
            day_end_time='17:00',
        )

        assert_that(results, has_entries(total=equal_to(10)))

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **{'from': '2020-10-06T08:00:00+00:00'},
                    until='2020-10-06T09:00:00+00:00',
                    agent_id=common_fields['agent_id'],
                    login_time=0,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T13:00:00+00:00'},
                    until='2020-10-06T14:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T16:00:00+00:00'},
                    until='2020-10-06T17:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 7:00:00', 'login_time': '01:00:00'})  # Tue
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 13:00:00', 'login_time': '01:00:00'})  # Wed
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-08 18:00:00', 'login_time': '01:00:00'})  # Thur
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-09 18:00:00', 'login_time': '01:00:00'})  # Fri
    # fmt: on
    def test_get_agent_when_call_not_in_week_days(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 00:00:00',
            until='2020-10-10 00:00:00',
            interval='day',
            week_days='3,4',  # Wed, Thur
        )
        assert_that(results, has_entries(total=equal_to(3)))

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-08T00:00:00+00:00'},
                    until='2020-10-09T00:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-10T00:00:00+00:00',
                    login_time=timedelta(hours=1 + 1).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-06 23:00:00', 'login_time': '01:00:00'})  # Mon
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 00:00:00', 'login_time': '01:00:00'})  # Tues
    # fmt:
    def test_get_agent_stats_week_days_hours_overlapping(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 23:00:00',
            until='2020-10-07 01:00:00',
            interval='hour',
            week_days='2',  # Tues
        )

        assert_that(results, has_entries(total=equal_to(2)))

        common_fields = {'tenant_uuid': MASTER_TENANT, 'agent_id': 42, 'agent_number': '1001'}
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                )
            ),
        )

        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 23:00:00',
            until='2020-10-07 01:00:00',
            interval='hour',
            week_days='3',  # Wed
        )

        assert_that(results, has_entries(total=equal_to(2)))

        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T23:00:00+00:00'},
                    until='2020-10-07T01:00:00+00:00',
                    login_time=timedelta(hours=1).total_seconds()
                )
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-05 23:00:00', 'login_time': '00:51:00'})  # Out
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 00:00:00', 'login_time': '00:52:00'})  # Out
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 15:00:00', 'login_time': '00:53:00'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-07 23:00:00', 'login_time': '00:54:00'})  # Out
    # fmt: on
    def test_get_agent_stat_with_day_interval_and_time_period(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 00:00:00',
            until='2020-10-08 00:00:00',
            interval='day',
            day_start_time='08:00',
            day_end_time='17:00',
        )

        assert_that(results, has_entries(total=equal_to(3)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                    login_time=0,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-07T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    login_time=timedelta(minutes=53).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-08T00:00:00+00:00',
                    login_time=timedelta(minutes=53).total_seconds(),
                ),
            ),
        )

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_that_get_agent_stats_by_day_when_no_stats(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-06 00:00:00',
            until='2020-10-07 00:00:00',
            interval='day',
        )

        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(results, has_entries(total=equal_to(2)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-06T00:00:00+00:00'},
                    until='2020-10-07T00:00:00+00:00',
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 23:00:00', 'login_time': '00:50:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-12 10:00:00', 'login_time': '00:51:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-14 15:00:00', 'login_time': '00:52:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-14 20:00:00', 'login_time': '00:53:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-17 10:00:00', 'login_time': '00:54:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-18 10:00:00', 'login_time': '00:55:00'})  # not counted
    # fmt: on
    def test_get_agent_stat_with_month_interval_and_time_period(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-01T00:00:00+00:00',
            until='2020-11-01T00:00:00+00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
        )

        assert_that(results, has_entries(total=equal_to(2)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-01T00:00:00+00:00'},
                    until='2020-11-01T00:00:00+00:00',
                    login_time=timedelta(minutes=51 + 52).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-01T00:00:00+00:00'},
                    until='2020-11-01T00:00:00+00:00',
                    login_time=timedelta(minutes=51 + 52).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-01-01T06:00:00+00:00', 'login_time': '00:55:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-02-12T10:00:00+00:00', 'login_time': '00:56:00'})  # should be counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-03-31T15:00:00+00:00', 'login_time': '00:57:00'})  # should be counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-03-31T18:00:00+00:00', 'login_time': '00:58:00'})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_months_with_all_filters(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-01-01T00:00:00+00:00',
            until='2020-04-01T00:00:00+00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
        )

        assert_that(results, has_entries(total=equal_to(4)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-01-01T00:00:00+00:00'},
                    until='2020-02-01T00:00:00+00:00',
                    login_time=0,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-02-01T00:00:00+00:00'},
                    until='2020-03-01T00:00:00+00:00',
                    login_time=timedelta(minutes=56).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-03-01T00:00:00+00:00'},
                    until='2020-04-01T00:00:00+00:00',
                    login_time=timedelta(minutes=57).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-01-01T00:00:00+00:00'},
                    until='2020-04-01T00:00:00+00:00',
                    login_time=timedelta(minutes=56 + 57).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-01-01T06:00:00-05:00', 'login_time': '00:55:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-02-12T10:00:00-05:00', 'login_time': '00:56:00'})  # should be counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-03-31T15:00:00-04:00', 'login_time': '00:57:00'})  # should be counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-03-31T18:00:00-04:00', 'login_time': '00:58:00'})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_months_with_all_filters_and_timezone(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-01-01T00:00:00',
            until='2020-04-01T00:00:00',
            interval='month',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3',
            timezone='America/Montreal',
        )

        assert_that(results, has_entries(total=equal_to(4)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-01-01T00:00:00-05:00'},
                    until='2020-02-01T00:00:00-05:00',
                    login_time=0,
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-02-01T00:00:00-05:00'},
                    until='2020-03-01T00:00:00-05:00',
                    login_time=timedelta(minutes=56).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-03-01T00:00:00-05:00'},
                    until='2020-04-01T00:00:00-04:00',
                    login_time=timedelta(minutes=57).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-01-01T00:00:00-05:00'},
                    until='2020-04-01T00:00:00-04:00',
                    login_time=timedelta(minutes=56 + 57).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-31T17:00:00-04:00', 'login_time': '00:50:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-31T18:00:00-04:00', 'login_time': '00:51:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T08:00:00-05:00', 'login_time': '00:52:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T16:00:00-05:00', 'login_time': '00:53:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-02T7:00:00-05:00', 'login_time': '00:54:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-02T8:00:00-05:00', 'login_time': '00:55:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-02T16:00:00-05:00', 'login_time': '00:56:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-02T18:00:00-05:00', 'login_time': '00:57:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-03T16:00:00-05:00', 'login_time': '00:58:00'})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_days_with_all_filters_and_timezone(self):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-31T00:00:00-04:00',
            until='2020-11-03T00:00:00-05:00',
            interval='day',
            day_start_time='08:00',
            day_end_time='17:00',
            week_days='1,2,3,4,5,7',
            timezone='America/Montreal',
        )

        assert_that(results, has_entries(total=equal_to(3)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-02T00:00:00-05:00',
                    login_time=timedelta(minutes=52 + 53).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-02T00:00:00-05:00'},
                    until='2020-11-03T00:00:00-05:00',
                    login_time=timedelta(minutes=55 + 56).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T00:00:00-04:00'},
                    until='2020-11-03T00:00:00-05:00',
                    login_time=timedelta(minutes=52 + 53 + 55 + 56).total_seconds(),
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-31T17:00:00-04:00', 'login_time': '00:50:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-31T18:00:00-04:00', 'login_time': '00:51:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T00:00:00-04:00', 'login_time': '00:52:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T01:00:00-04:00', 'login_time': '00:53:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T01:00:00-05:00', 'login_time': '00:54:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T02:00:00-05:00', 'login_time': '00:55:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T03:00:00-05:00', 'login_time': '00:56:00'})  # counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-01T04:00:00-05:00', 'login_time': '00:57:00'})  # not counted
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-11-02T02:00:00-05:00', 'login_time': '00:58:00'})  # not counted
    # fmt: on
    def test_monthly_interval_multiple_hours_with_all_filters_and_timezone_dst_change(
        self,
    ):
        results = self.call_logd.agent_statistics.get_by_id(
            agent_id=42,
            from_='2020-10-31T00:00:00-04:00',  # DST change happens on 2020-11-01 02:00
            until='2020-11-02T03:00:00-05:00',
            interval='hour',
            day_start_time='00:00',
            day_end_time='03:00',
            week_days='2,3,4,5,7',
            timezone='America/Montreal',
        )

        assert_that(results, has_entries(total=equal_to(4)))
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'agent_id': 42,
            'agent_number': '1001',
        }
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-01T01:00:00-05:00',
                    login_time=timedelta(minutes=52 + 53).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T01:00:00-05:00'},
                    until='2020-11-01T02:00:00-05:00',
                    login_time=timedelta(minutes=54).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T02:00:00-05:00'},
                    until='2020-11-01T03:00:00-05:00',
                    login_time=timedelta(minutes=55).total_seconds(),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T00:00:00-04:00'},
                    until='2020-11-02T03:00:00-05:00',
                    login_time=timedelta(
                        minutes=52 + 53 + 54 + 55 + 56
                    ).total_seconds(),
                ),
            ),
        )
