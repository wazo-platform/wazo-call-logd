# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import (
    datetime as dt,
    timezone as tz,
    timedelta as td,
)
from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
)

from .helpers.base import DBIntegrationTest
from .helpers.constants import OTHER_TENANT, USERS_TENANT
from .helpers.database import stat_agent, stat_call_on_queue, stat_agent_periodic


class TestAgentStat(DBIntegrationTest):
    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent({'id': 2, 'name': 'Agent/1002', 'agent_id': 10})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:00:10', 'talktime': 10, 'status': 'answered'})  # Out
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 14:05:00', 'talktime': 11, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 15:01:00', 'talktime': 12, 'status': 'answered'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Out
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 15:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 14:10:00', 'talktime': 13, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 15:23:00', 'talktime': 0, 'status': 'abandoned'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 16:59:00', 'talktime': 14, 'status': 'answered'})  # Out
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:03:00', 'wrapup_time': '00:00:00'})  # In
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 15:00:00', 'login_time': '01:00:00', 'pause_time': '00:05:00', 'wrapup_time': '00:05:00'})  # In
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 16:00:00', 'login_time': '00:35:00', 'pause_time': '00:11:00', 'wrapup_time': '00:05:00'})  # Out
    # fmt: on
    def test_get_interval_group_by_agents_all_fields(self):
        tenant_uuids = None
        interval = {
            'from_': dt(2020, 10, 1, 14, 0, 0, tzinfo=tz.utc),
            'until': dt(2020, 10, 1, 16, 0, 0, tzinfo=tz.utc),
        }

        result = self.dao.agent_stat.get_interval(tenant_uuids, **interval)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 12).seconds,
                    login_time=td(hours=1, minutes=30).seconds,
                    pause_time=td(minutes=15).seconds,
                    wrapup_time=td(minutes=5, seconds=42).seconds,
                ),
                has_entries(
                    agent_id=10,
                    agent_number='1002',
                    answered=1,
                    conversation_time=td(seconds=13 + 0).seconds,
                    login_time=td(hours=2).seconds,
                    pause_time=td(minutes=3 + 5).seconds,
                    wrapup_time=td(minutes=5).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 14:05:00', 'talktime': 11, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 15:01:00', 'talktime': 12, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'talktime': 900, 'status': 'answered'})  # Out
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 15:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Out
    # fmt: on
    def test_get_interval_include_limit(self):
        tenant_uuids = None
        interval = {
            'from_': dt(2020, 10, 1, 14, 0, 0, tzinfo=tz.utc),
            'until': dt(2020, 10, 1, 16, 0, 0, tzinfo=tz.utc),
        }

        result = self.dao.agent_stat.get_interval(tenant_uuids, **interval)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 12).seconds,
                    login_time=td(hours=1, minutes=30).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 14:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'talktime': 900, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    # fmt: on
    def test_get_interval_without_filters(self):
        tenant_uuids = None
        result = self.dao.agent_stat.get_interval(tenant_uuids)

        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 900).seconds,
                    login_time=td(hours=1 + 1).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 14:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 15:01:00', 'talktime': 12, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'talktime': 900, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 15:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 16:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    # fmt: on
    def test_get_interval_with_start_end_time(self):
        tenant_uuids = None
        kwargs = {'start_time': 14, 'end_time': 15}
        result = self.dao.agent_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 12).seconds,
                    login_time=td(hours=1, minutes=30).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 03:05:00+0000', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 05:01:00+0000', 'talktime': 12, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 06:00:00+0000', 'talktime': 900, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 03:00:00+0000', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 05:00:00+0000', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 06:00:00+0000', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})
    # fmt: on
    def test_get_interval_with_start_end_time_follows_timezone(self):
        tenant_uuids = None
        kwargs = {
            'start_time': 9,  # = 4 UTC
            'end_time': 10,  # = 5 UTC
            'from_': dt(2020, 9, 1, 0, 0, 0, tzinfo=tz(td(hours=5))),
        }
        result = self.dao.agent_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=1,
                    conversation_time=td(seconds=12).seconds,
                    login_time=td(minutes=30).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-02 13:15:00', 'talktime': 12, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-03 13:22:00', 'talktime': 900, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-04 13:44:00', 'talktime': 654, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # Thursday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-02 13:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})  # Friday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-03 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Saturday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-04 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Sunday
    # fmt: on
    def test_get_interval_with_week_days(self):
        tenant_uuids = None
        kwargs = {'week_days': [1, 2, 3, 4, 5]}
        result = self.dao.agent_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 12).seconds,
                    login_time=td(hours=1, minutes=30).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-02 13:15:00', 'talktime': 12, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-03 13:22:00', 'talktime': 900, 'status': 'answered'})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-04 13:44:00', 'talktime': 654, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # Thursday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-02 13:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})  # Friday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-03 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Saturday
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-04 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Sunday
    # fmt: on
    def test_get_interval_with_week_days_follows_timezone(self):
        tenant_uuids = None
        kwargs = {
            'from_': dt(2020, 9, 1, 0, 0, 0, tzinfo=tz(td(hours=12))),
            'week_days': [1, 2, 3, 4, 5],
        }
        result = self.dao.agent_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    agent_id=42,
                    agent_number='1001',
                    answered=2,
                    conversation_time=td(seconds=11 + 654).seconds,
                    login_time=td(hours=1 + 1).seconds,
                ),
            ),
        )

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # Thursday
    # fmt: on
    def test_get_interval_empty_week_days(self):
        tenant_uuids = None
        kwargs = {'week_days': []}
        result = self.dao.agent_stat.get_interval(tenant_uuids, **kwargs)
        assert_that(result, empty())

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:05:00', 'talktime': 11, 'status': 'answered'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})
    # fmt: on
    def test_get_interval_filtered_by_empty_tenant(self):
        tenant_uuids = []
        result = self.dao.agent_stat.get_interval(tenant_uuids)
        assert_that(result, empty())

    # fmt: off
    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent({'id': 2, 'name': 'Agent/1002', 'agent_id': 10})
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 13:00:10', 'talktime': 10, 'status': 'answered'})  # Out
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 14:05:00', 'talktime': 11, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 1, 'time': '2020-10-01 15:01:00', 'talktime': 12, 'status': 'answered'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00', 'login_time': '01:00:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:00'})  # Out
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:15:00', 'wrapup_time': '00:05:00'})  # In
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 15:00:00', 'login_time': '00:30:00', 'pause_time': '00:00:00', 'wrapup_time': '00:00:42'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 14:10:00', 'talktime': 13, 'status': 'answered'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 15:23:00', 'talktime': 0, 'status': 'abandoned'})  # In
    @stat_call_on_queue({'agent_id': 2, 'time': '2020-10-01 16:59:00', 'talktime': 14, 'status': 'answered'})  # Out
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 14:00:00', 'login_time': '01:00:00', 'pause_time': '00:03:00', 'wrapup_time': '00:00:00'})  # In
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 15:00:00', 'login_time': '01:00:00', 'pause_time': '00:05:00', 'wrapup_time': '00:05:00'})  # In
    @stat_agent_periodic({'agent_id': 2, 'time': '2020-10-01 16:00:00', 'login_time': '00:35:00', 'pause_time': '00:11:00', 'wrapup_time': '00:05:00'})  # Out
    # fmt: on
    def test_get_interval_by_agent_all_fields(self):
        tenant_uuids = None
        interval = {
            'from_': dt(2020, 10, 1, 14, 0, 0, tzinfo=tz.utc),
            'until': dt(2020, 10, 1, 16, 0, 0, tzinfo=tz.utc),
        }

        result = self.dao.agent_stat.get_interval_by_agent(tenant_uuids, 42, **interval)
        assert_that(
            result,
            has_entries(
                agent_id=42,
                agent_number='1001',
                answered=2,
                conversation_time=td(seconds=11 + 12).seconds,
                login_time=td(hours=1, minutes=30).seconds,
                pause_time=td(minutes=15).seconds,
                wrapup_time=td(minutes=5, seconds=42).seconds,
            ),
        )

    def test_get_interval_by_agent_without_result(self):
        tenant_uuids = None
        result = self.dao.agent_stat.get_interval_by_agent(tenant_uuids, 1)
        assert_that(result, equal_to(None))

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 14:00:00'})
    @stat_agent_periodic({'agent_id': 1, 'time': '2020-10-01 13:00:00'})
    def test_find_oldest_time(self):
        result = self.dao.agent_stat.find_oldest_time(42)
        assert_that(result.isoformat(), equal_to('2020-10-01T13:00:00+00:00'))

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_find_oldest_time_when_empty(self):
        result = self.dao.queue_stat.find_oldest_time(42)
        assert_that(result, equal_to(None))

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_get_stat_agent(self):
        result = self.dao.agent_stat.get_stat_agent(42)
        assert_that(result, has_entries(agent_id=42, number='1001'))

    # fmt: off
    @stat_agent({'id': 1, 'agent_id': 42, 'name': 'Agent/1001', 'tenant_uuid': USERS_TENANT})
    @stat_agent({'id': 2, 'agent_id': 24, 'name': 'Agent/1005', 'tenant_uuid': OTHER_TENANT})
    # fmt: on
    def test_get_stat_agent_filtered_by_tenant(self):
        result = self.dao.agent_stat.get_stat_agent(42, tenant_uuids=[USERS_TENANT])
        assert_that(result, has_entries(agent_id=42))

        result = self.dao.agent_stat.get_stat_agent(
            42, tenant_uuids=[USERS_TENANT, OTHER_TENANT]
        )
        assert_that(result, has_entries(agent_id=42))

        result = self.dao.agent_stat.get_stat_agent(42, tenant_uuids=[OTHER_TENANT])
        assert_that(result, equal_to(None))

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_get_stat_agent_no_filtering(self):
        result = self.dao.agent_stat.get_stat_agent(42)
        assert_that(result, has_entries(agent_id=42))

    @stat_agent({'id': 1, 'name': 'Agent/1001', 'agent_id': 42})
    def test_get_stat_agent_when_searching_in_no_tenants(self):
        result = self.dao.agent_stat.get_stat_agent(42, tenant_uuids=[])
        assert_that(result, equal_to(None))

    @stat_agent({'agent_id': 1, 'name': 'Agent/1001', 'tenant_uuid': USERS_TENANT})
    @stat_agent({'agent_id': 2, 'name': 'Agent/1002', 'tenant_uuid': OTHER_TENANT})
    def test_get_stat_agents(self):
        result = self.dao.agent_stat.get_stat_agents()
        assert_that(
            result,
            contains_inanyorder(
                has_entries(agent_id=1, number='1001', tenant_uuid=USERS_TENANT),
                has_entries(agent_id=2, number='1002', tenant_uuid=OTHER_TENANT),
            ),
        )

    # fmt: off
    @stat_agent({'id': 10, 'agent_id': 1, 'name': 'Agent/1001', 'tenant_uuid': USERS_TENANT})
    @stat_agent({'id': 12, 'agent_id': 2, 'name': 'Agent/1002', 'tenant_uuid': OTHER_TENANT})
    # fmt: on
    def test_get_stat_agents_filtered_by_tenant(self):
        result = self.dao.agent_stat.get_stat_agents([USERS_TENANT])
        assert_that(
            result,
            contains_inanyorder(
                has_entries(agent_id=1),
            ),
        )

        result = self.dao.agent_stat.get_stat_agents([USERS_TENANT, OTHER_TENANT])
        assert_that(
            result,
            contains_inanyorder(
                has_entries(agent_id=1),
                has_entries(agent_id=2),
            ),
        )

        result = self.dao.agent_stat.get_stat_agents([OTHER_TENANT])
        assert_that(
            result,
            contains_inanyorder(
                has_entries(agent_id=2),
            ),
        )

    # fmt: off
    @stat_agent({'id': 11, 'agent_id': 1, 'name': 'Agent/1001', 'tenant_uuid': USERS_TENANT})
    # fmt: on
    def test_get_stat_agents_empty_tenant(self):
        result = self.dao.agent_stat.get_stat_agents([])
        assert_that(result, empty())

    def test_get_stat_agents_when_no_agent(self):
        result = self.dao.agent_stat.get_stat_agents()
        assert_that(result, empty())
