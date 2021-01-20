# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    has_items,
)
from .helpers.base import IntegrationTest
from .helpers.constants import MASTER_TENANT
from .helpers.database import stat_call_on_queue, stat_queue, stat_queue_periodic


class TestQueueStatisticsQOS(IntegrationTest):

    asset = 'base'

    # fmt: off
    # Following is NOT in open hours/open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00-04:00', 'waittime': 15, 'status': 'abandoned'})
    # Following is in open hours/open days
    # 2020-10-31 11:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'total': 8, 'answered': 5, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # 2020-10-31 13:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T13:00:00-04:00', 'total': 6, 'answered': 3, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:18:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T13:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # fmt: on
    def test_period_thresholds_by_hour_all_params(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(
            queue_id=1,
            from_='2020-10-30T00:00:00-04:00',
            until='2020-11-01T00:00:00-04:00',
            interval='hour',
            day_start_time='10:00',
            day_end_time='15:00',
            week_days='2,3,4,6',
            timezone='America/Montreal',
            qos_thresholds='5,10,15,20,30',
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(6)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T11:00:00-04:00'},
                    until='2020-10-31T12:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=1),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T13:00:00-04:00'},
                    until='2020-10-31T14:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=0, abandoned=1),
                        has_entries(min=15, max=20, answered=0, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-30T00:00:00-04:00'},
                    until='2020-11-01T00:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=2, abandoned=2),
                        has_entries(min=5, max=10, answered=2, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=2),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=2, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=2),
                    ),
                ),
            ),
        )

    # fmt: off
    # Following is NOT in open hours/open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T11:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T11:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T04:00:00-05:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T04:12:00-05:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T05:00:00-05:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T05:12:00-05:00', 'waittime': 15, 'status': 'abandoned'})
    # Following is in open hours/open days
    # 2020-11-01 00:00-04
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T00:00:00-04:00', 'total': 9, 'answered': 6, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:55:00-04:00', 'waittime': 13, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T00:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # 2020-11-01 01:00-04
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T01:00:00-04:00', 'total': 9, 'answered': 6, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:55:00-04:00', 'waittime': 13, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # 2020-11-01 01:00-05
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T01:00:00-05:00', 'total': 8, 'answered': 5, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:00:00-05:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:12:00-05:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:20:00-05:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:45:00-05:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:59:00-05:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:05:00-05:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:10:00-05:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T01:30:00-05:00', 'waittime': 30, 'status': 'abandoned'})
    # 2020-11-01 02:00-05
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T02:00:00-05:00', 'total': 6, 'answered': 3, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:00:00-05:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:12:00-05:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:18:00-05:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:05:00-05:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:10:00-05:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T02:30:00-05:00', 'waittime': 30, 'status': 'abandoned'})
    # fmt: on
    def test_period_thresholds_by_hour_all_params_and_dst_change(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(
            queue_id=1,
            from_='2020-11-01T00:00:00-04:00',
            until='2020-11-01T03:00:00-05:00',
            interval='hour',
            day_start_time='00:00',
            day_end_time='03:00',
            week_days='2,3,4,6,7',
            timezone='America/Montreal',
            qos_thresholds='5,10,15,20,30',
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(4)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-01T01:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=2, abandoned=2),
                        has_entries(min=5, max=10, answered=2, abandoned=0),
                        has_entries(min=10, max=15, answered=4, abandoned=2),
                        has_entries(min=15, max=20, answered=2, abandoned=0),
                        has_entries(min=20, max=30, answered=2, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=2),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T01:00:00-05:00'},
                    until='2020-11-01T02:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=1),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T02:00:00-05:00'},
                    until='2020-11-01T03:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=0, abandoned=1),
                        has_entries(min=15, max=20, answered=0, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-01T03:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=4, abandoned=4),
                        has_entries(min=5, max=10, answered=4, abandoned=0),
                        has_entries(min=10, max=15, answered=5, abandoned=4),
                        has_entries(min=15, max=20, answered=3, abandoned=0),
                        has_entries(min=20, max=30, answered=4, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=4),
                    ),
                ),
            ),
        )

    # fmt: off
    # Following is NOT in open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    # Following is in open days but NOT in open hours and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00-04:00', 'waittime': 15, 'status': 'abandoned'})
    # Following is both in open days and open hours and is counted
    # 2020-10-31 11:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'total': 8, 'answered': 5, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # Following is both in open days and open hours and is counted
    # 2020-11-01 13:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T13:00:00-04:00', 'total': 6, 'answered': 3, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:18:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # Following is NOT in open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-02T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    # fmt: on
    def test_period_thresholds_by_day_all_params(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(
            queue_id=1,
            from_='2020-10-30T00:00:00-04:00',
            until='2020-11-03T00:00:00-05:00',
            interval='day',
            day_start_time='10:00',
            day_end_time='15:00',
            week_days='2,3,4,6,7',
            timezone='America/Montreal',
            qos_thresholds='5,10,15,20,30',
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(3)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-31T00:00:00-04:00'},
                    until='2020-11-01T00:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=1),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-11-02T00:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=0, abandoned=1),
                        has_entries(min=15, max=20, answered=0, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-30T00:00:00-04:00'},
                    until='2020-11-03T00:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=2, abandoned=2),
                        has_entries(min=5, max=10, answered=2, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=2),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=2, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=2),
                    ),
                ),
            ),
        )

    # fmt: off
    # Following is NOT in open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    # Following is in open days but NOT in open hours and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00-04:00', 'waittime': 15, 'status': 'abandoned'})
    # Following is both in open days and open hours and is counted
    # 2020-10-31 11:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'total': 8, 'answered': 5, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:20:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:45:00-04:00', 'waittime': 10, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:59:00-04:00', 'waittime': 15, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T11:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # Following is both in open days and open hours and is counted
    # 2020-11-01 13:00
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-01T13:00:00-04:00', 'total': 6, 'answered': 3, 'abandoned': 3})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:00:00-04:00', 'waittime': 20, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:12:00-04:00', 'waittime': 5, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:18:00-04:00', 'waittime': 3, 'status': 'answered'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:05:00-04:00', 'waittime': 2, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:10:00-04:00', 'waittime': 14, 'status': 'abandoned'})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-01T13:30:00-04:00', 'waittime': 30, 'status': 'abandoned'})
    # Following is NOT in open days and not counted
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-11-02T011:00:00-04:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-11-02T011:12:00-04:00', 'waittime': 10, 'status': 'answered'})
    # fmt: on
    def test_period_thresholds_by_month_all_params(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(
            queue_id=1,
            from_='2020-10-01T00:00:00-04:00',
            until='2020-12-01T00:00:00-05:00',
            interval='month',
            day_start_time='10:00',
            day_end_time='15:00',
            week_days='2,3,4,6,7',
            timezone='America/Montreal',
            qos_thresholds='5,10,15,20,30',
        )
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(3)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-01T00:00:00-04:00'},
                    until='2020-11-01T00:00:00-04:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=1),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-11-01T00:00:00-04:00'},
                    until='2020-12-01T00:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=1, abandoned=1),
                        has_entries(min=5, max=10, answered=1, abandoned=0),
                        has_entries(min=10, max=15, answered=0, abandoned=1),
                        has_entries(min=15, max=20, answered=0, abandoned=0),
                        has_entries(min=20, max=30, answered=1, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=1),
                    ),
                ),
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-01T00:00:00-04:00'},
                    until='2020-12-01T00:00:00-05:00',
                    quality_of_service=has_items(
                        has_entries(min=0, max=5, answered=2, abandoned=2),
                        has_entries(min=5, max=10, answered=2, abandoned=0),
                        has_entries(min=10, max=15, answered=1, abandoned=2),
                        has_entries(min=15, max=20, answered=1, abandoned=0),
                        has_entries(min=20, max=30, answered=2, abandoned=0),
                        has_entries(min=30, max=None, answered=0, abandoned=2),
                    ),
                ),
            ),
        )

    # fmt: off
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-30T011:00:00+00:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-30T011:12:00+00:00', 'waittime': 10, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T09:00:00+00:00', 'total': 1, 'answered': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T09:12:00+00:00', 'waittime': 5, 'status': 'answered'})
    @stat_queue_periodic({'queue_id': 1, 'time': '2020-10-31T16:00:00+00:00', 'total': 1, 'abandoned': 1})
    @stat_call_on_queue({'queue_id': 1, 'time': '2020-10-31T16:12:00+00:00', 'waittime': 15, 'status': 'abandoned'})
    # fmt: on
    def test_period_thresholds_no_param(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(queue_id=1)
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': '2020-10-30T11:00:00+00:00'},
                    until=self._get_tomorrow(),
                    quality_of_service=has_items(
                        has_entries(min=0, max=None, answered=2, abandoned=1),
                    ),
                ),
            ),
        )

    @stat_queue({'queue_id': 1})
    def test_period_thresholds_no_stats(self):
        results = self.call_logd.queue_statistics.get_qos_by_id(queue_id=1)
        common_fields = {
            'tenant_uuid': MASTER_TENANT,
            'queue_id': 1,
            'queue_name': 'queue',
        }

        assert_that(results, has_entries(total=equal_to(1)))
        assert_that(
            results['items'],
            has_items(
                has_entries(
                    **common_fields,
                    **{'from': None},
                    until=self._get_tomorrow(),
                    quality_of_service=has_items(
                        has_entries(min=0, max=None, answered=0, abandoned=0),
                    ),
                ),
            ),
        )
